"""
WearPark Neurological Simulator
================================
Simule une journée complète de données de poignet pour un patient
présentant des épisodes de tremblements neurologiques (Parkinson ou
tremblement essentiel), et les envoie au backend via le protocole
TCP binaire exact du vrai appareil.

Usage:
    python simulator.py --date 2024-03-15 --attacks 5
    python simulator.py --date 2024-03-15 --attacks 3 --tremor-type essential
    python simulator.py --date 2024-03-15 --attacks 4 --tremor-type both --speed realtime
    python simulator.py --help

Modes de vitesse:
    fast        Envoie tout aussi vite que possible (défaut)
    realtime    Respecte le timing réel (1s simulée = 1s réelle)
    --speed N   Facteur d'accélération (ex: --speed 60 = 1 min simulée par seconde)

Structure d'une journée:
    - 24h de données à --hz Hz
    - N attaques réparties aléatoirement dans la journée
    - Chaque attaque : calme → montée → tremblement intense → descente → calme
    - Entre les attaques : signal de repos (légères micro-vibrations)
"""

import argparse
import math
import random
import socket
import ssl
import struct
import sys
import time
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Protocol (reproduction exacte de protocol.py)
# ---------------------------------------------------------------------------

_ENDIAN = "<"
TYPE_AUTH   = 0
TYPE_SINGLE = 1
_AUTH_FMT   = _ENDIAN + "B q"
_SINGLE_FMT = _ENDIAN + "B I 6f"


def epoch_ms() -> int:
    return int(time.time() * 1000)


def encode_auth_frame(timestamp_ms: int | None = None) -> bytes:
    if timestamp_ms is None:
        timestamp_ms = epoch_ms()
    return struct.pack(_AUTH_FMT, TYPE_AUTH, int(timestamp_ms))


@dataclass(frozen=True)
class Sample:
    ms_offset: int
    ax: float
    ay: float
    az: float
    gx: float
    gy: float
    gz: float


def encode_single_frame(sample: Sample) -> bytes:
    return struct.pack(
        _SINGLE_FMT,
        TYPE_SINGLE,
        int(sample.ms_offset),
        float(sample.ax), float(sample.ay), float(sample.az),
        float(sample.gx), float(sample.gy), float(sample.gz),
    )


# ---------------------------------------------------------------------------
# Modèles de tremblements neurologiques
# ---------------------------------------------------------------------------

@dataclass
class TremorProfile:
    """Profil physiologique d'un type de tremblement."""
    name: str
    freq_hz: float          # Fréquence centrale du tremblement
    freq_jitter: float      # ± variation de fréquence (Hz)
    amp_acc: float          # Amplitude accéléromètre (m/s²) au pic
    amp_gyro: float         # Amplitude gyroscope (rad/s) au pic
    dominant_axes: Tuple    # Pondération relative (ax, ay, az)
    rise_time_s: float      # Durée de montée du tremblement
    fall_time_s: float      # Durée de descente


TREMOR_PROFILES = {
    "parkinson": TremorProfile(
        name="Parkinson (repos, 4-6 Hz)",
        freq_hz=5.0,
        freq_jitter=0.8,
        amp_acc=2.5,
        amp_gyro=0.6,
        dominant_axes=(0.7, 0.9, 0.3),
        rise_time_s=3.0,
        fall_time_s=4.0,
    ),
    "essential": TremorProfile(
        name="Tremblement essentiel (action, 8-12 Hz)",
        freq_hz=10.0,
        freq_jitter=1.5,
        amp_acc=3.8,
        amp_gyro=1.1,
        dominant_axes=(0.9, 0.6, 0.2),
        rise_time_s=1.5,
        fall_time_s=2.5,
    ),
}


class NeurologicalSensorSimulator:
    """
    Génère des données réalistes d'accéléromètre/gyroscope pour un poignet
    avec épisodes de tremblements neurologiques.

    Utilise le temps simulé (sim_s) plutôt que le temps réel pour calculer
    la phase — indispensable en mode fast où dt réel ≈ 0.

    Unités identiques au vrai ICM-20948 Adafruit :
      - Accéléromètre : m/s²  (gravité ≈ 9.81 m/s² sur Z au repos)
      - Gyroscope     : rad/s
    """

    def __init__(self):
        self._intensity = 0.0
        self._profile: Optional[TremorProfile] = None
        # Fréquence de dérive par tranche de 2s simulées
        self._freq_override: Optional[float] = None
        self._last_drift_s = 0.0

    def set_intensity(self, intensity: float, profile: TremorProfile) -> None:
        self._intensity = max(0.0, min(1.0, intensity))
        self._profile = profile

    def set_idle(self) -> None:
        self._intensity = 0.0
        self._profile = None

    def read(self, sim_s: float) -> Tuple[float, float, float, float, float, float]:
        """
        sim_s : temps simulé en secondes depuis minuit.
                Utilisé pour calculer la phase — correct en mode fast et realtime.
        """
        if self._profile and self._intensity > 0.001:
            p = self._profile

            # Dérive de fréquence toutes les 2s simulées
            if sim_s - self._last_drift_s > 2.0:
                self._freq_override = p.freq_hz + random.gauss(0, p.freq_jitter * 0.3)
                self._freq_override = max(p.freq_hz - p.freq_jitter,
                                          min(p.freq_hz + p.freq_jitter, self._freq_override))
                self._last_drift_s = sim_s

            freq = self._freq_override if self._freq_override else p.freq_hz

            # Phase basée sur le temps simulé — correcte quelle que soit la vitesse
            phase = 2 * math.pi * freq * sim_s
            sin_v = math.sin(phase)
            cos_v = math.cos(phase * 1.07 + 0.4)

            i  = self._intensity
            da = p.dominant_axes

            ax = da[0] * p.amp_acc * i * sin_v               + random.gauss(0, 0.08 + 0.05 * i)
            ay = da[1] * p.amp_acc * i * cos_v * 0.8         + random.gauss(0, 0.08 + 0.05 * i)
            az = 9.81 + da[2] * p.amp_acc * i * sin_v * 0.4  + random.gauss(0, 0.05)
            gx = da[0] * p.amp_gyro * i * cos_v              + random.gauss(0, 0.008 + 0.005 * i)
            gy = da[1] * p.amp_gyro * i * sin_v * 0.7        + random.gauss(0, 0.008 + 0.005 * i)
            gz = da[2] * p.amp_gyro * i * cos_v * 0.3        + random.gauss(0, 0.005)
        else:
            # Repos : micro-vibrations (pouls ~1.2 Hz) basées sur le temps simulé
            phase = 2 * math.pi * 1.2 * sim_s
            micro = math.sin(phase) * 0.04
            ax = micro * 0.3  + random.gauss(0, 0.03)
            ay = micro        + random.gauss(0, 0.03)
            az = 9.81         + random.gauss(0, 0.02)
            gx = micro * 0.01 + random.gauss(0, 0.003)
            gy = micro * 0.01 + random.gauss(0, 0.003)
            gz =                random.gauss(0, 0.002)

        return ax, ay, az, gx, gy, gz


# ---------------------------------------------------------------------------
# Planificateur de journée
# ---------------------------------------------------------------------------

@dataclass
class AttackWindow:
    """Un épisode de tremblement dans la journée simulée."""
    start_s: float
    calm_before_s: float
    rise_s: float
    peak_s: float
    fall_s: float
    calm_after_s: float
    profile: TremorProfile

    @property
    def total_s(self) -> float:
        return self.calm_before_s + self.rise_s + self.peak_s + self.fall_s + self.calm_after_s

    @property
    def end_s(self) -> float:
        return self.start_s + self.total_s


def build_day_schedule(n_attacks: int, tremor_type: str, seed: int | None = None) -> List[AttackWindow]:
    """
    Génère N attaques aléatoires réparties dans une journée de 24h.
    Les attaques ne se chevauchent pas et sont espacées d'au moins 30 min.
    """
    rng = random.Random(seed)
    day_s = 24 * 3600

    available = []
    if tremor_type in ("parkinson", "both"):
        available.append(TREMOR_PROFILES["parkinson"])
    if tremor_type in ("essential", "both"):
        available.append(TREMOR_PROFILES["essential"])

    attacks: List[AttackWindow] = []
    min_gap_s = 30 * 60

    attempts = 0
    while len(attacks) < n_attacks and attempts < 1000:
        attempts += 1
        profile = rng.choice(available)

        calm_before = rng.uniform(60, 300)
        peak        = rng.uniform(30, 180)
        calm_after  = rng.uniform(60, 240)
        total       = calm_before + profile.rise_time_s + peak + profile.fall_time_s + calm_after

        start = rng.uniform(2 * 3600, day_s - total - 2 * 3600)
        end   = start + total

        overlap = any(
            not (end + min_gap_s <= a.start_s or start >= a.end_s + min_gap_s)
            for a in attacks
        )
        if overlap:
            continue

        attacks.append(AttackWindow(
            start_s=start,
            calm_before_s=calm_before,
            rise_s=profile.rise_time_s,
            peak_s=peak,
            fall_s=profile.fall_time_s,
            calm_after_s=calm_after,
            profile=profile,
        ))

    attacks.sort(key=lambda a: a.start_s)
    return attacks


# ---------------------------------------------------------------------------
# Queue en mémoire
# ---------------------------------------------------------------------------

class MemQueue:
    def __init__(self, maxlen: int):
        self._q: Deque[Sample] = deque()
        self._maxlen = max(1, int(maxlen))

    def push(self, s: Sample) -> None:
        self._q.append(s)
        for _ in range(max(0, len(self._q) - self._maxlen)):
            self._q.popleft()

    def pop(self) -> Sample | None:
        return self._q.popleft() if self._q else None

    def __len__(self) -> int:
        return len(self._q)


# ---------------------------------------------------------------------------
# Client TCP
# ---------------------------------------------------------------------------

class TcpClient:
    def __init__(self, host: str, port: int, connect_timeout: float = 5.0,
                 io_timeout: float = 30.0, tls: bool = False,
                 ca_cert: str = "", client_cert: str = "", client_key: str = ""):
        self.host, self.port = host, port
        self.connect_timeout = connect_timeout
        self.io_timeout = io_timeout
        self.tls = tls
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        print(f"[TCP] Connexion à {self.host}:{self.port}...")
        sock = socket.create_connection((self.host, self.port), timeout=self.connect_timeout)
        sock.settimeout(self.io_timeout)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            pass
        if self.tls:
            if self.ca_cert:
                # Vérification du serveur avec la CA fournie
                ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self.ca_cert)
                ctx.check_hostname = False
            else:
                # Dev local — on ne vérifie pas le certificat du serveur
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            if self.client_cert and self.client_key:
                ctx.load_cert_chain(certfile=self.client_cert, keyfile=self.client_key)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            sock = ctx.wrap_socket(sock, server_hostname=None)
            print(f"[TLS] OK — {sock.cipher()[0]}")
        self.sock = sock
        print("[TCP] Connecté.")

    def close(self) -> None:
        try:
            if self.sock:
                self.sock.close()
        finally:
            self.sock = None

    def sendall(self, data: bytes) -> None:
        if not self.sock:
            raise RuntimeError("Non connecté")
        self.sock.sendall(data)

    def recv_until_newline(self, max_bytes: int = 4096) -> bytes:
        if not self.sock:
            raise RuntimeError("Non connecté")
        buf = bytearray()
        start = time.time()
        while len(buf) < max_bytes:
            if time.time() - start > self.io_timeout:
                self.close()
                raise RuntimeError("Timeout de réception")
            b = self.sock.recv(1)
            if not b:
                self.close()
                raise RuntimeError("Connexion fermée par le serveur")
            buf += b
            if b == b"\n":
                break
        return bytes(buf)


# ---------------------------------------------------------------------------
# Simulateur principal
# ---------------------------------------------------------------------------

class NeurologicalSimulator:

    def __init__(self, args):
        self.args = args
        self.sensor = NeurologicalSensorSimulator()
        self.client = TcpClient(
            host=args.host, port=args.port,
            connect_timeout=args.connect_timeout,
            io_timeout=args.io_timeout,
            tls=args.tls,
            ca_cert=getattr(args, "ca_cert", ""),
            client_cert=getattr(args, "client_cert", ""),
            client_key=getattr(args, "client_key", ""),
        )
        self.queue = MemQueue(500_000)
        self._stop = threading.Event()
        self._total_produced = 0
        self._total_sent = 0
        self._current_state = ""

        # Timestamp UTC de minuit pour la date simulée
        self.day_start_ms = self._parse_date_to_ms(args.date)

        # Planning de la journée
        self.schedule = build_day_schedule(
            n_attacks=args.attacks,
            tremor_type=args.tremor_type,
            seed=args.seed,
        )

        # Facteur de vitesse
        if args.speed == "fast":
            self.speed_factor = float("inf")
        elif args.speed == "realtime":
            self.speed_factor = 1.0
        else:
            try:
                self.speed_factor = float(args.speed)
                if self.speed_factor <= 0:
                    raise ValueError
            except ValueError:
                print(f"[WARN] --speed '{args.speed}' invalide, mode fast utilisé")
                self.speed_factor = float("inf")

    @staticmethod
    def _parse_date_to_ms(date_str: str) -> int:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            print(f"[ERROR] Format de date invalide: '{date_str}'. Utilisez YYYY-MM-DD.")
            sys.exit(1)

    def _print_schedule(self) -> None:
        print("\n" + "=" * 65)
        print(f"  Planning du {self.args.date}  —  {len(self.schedule)} attaque(s)")
        print("=" * 65)
        for i, a in enumerate(self.schedule, 1):
            h  = int(a.start_s // 3600)
            m  = int((a.start_s % 3600) // 60)
            eh = int(a.end_s // 3600)
            em = int((a.end_s % 3600) // 60)
            print(
                f"  #{i}  {h:02d}h{m:02d} → {eh:02d}h{em:02d}"
                f"  |  {a.profile.name}"
                f"  |  pic: {a.peak_s/60:.1f} min"
            )
        print("=" * 65 + "\n")

    def _get_state_at(self, sim_s: float) -> Tuple[float, Optional[TremorProfile]]:
        """Retourne (intensité 0.0-1.0, profil) pour un instant sim_s."""
        for a in self.schedule:
            if sim_s < a.start_s or sim_s > a.end_s:
                continue

            local = sim_s - a.start_s
            t1 = a.calm_before_s
            t2 = t1 + a.rise_s
            t3 = t2 + a.peak_s
            t4 = t3 + a.fall_s

            if local < t1:
                return 0.0, a.profile                               # Calme avant
            elif local < t2:
                return (local - t1) / a.rise_s, a.profile           # Montée
            elif local < t3:
                return 1.0, a.profile                               # Plateau
            elif local < t4:
                return 1.0 - (local - t3) / a.fall_s, a.profile    # Descente
            else:
                return 0.0, a.profile                               # Calme après

        return 0.0, None

    def _producer(self) -> None:
        hz = self.args.hz
        period_s = 1.0 / hz
        day_s    = 24 * 3600

        sleep_s = 0.0 if math.isinf(self.speed_factor) else period_s / self.speed_factor

        sim_s = 0.0
        print(f"[PRODUCER] Démarrage — {day_s * hz:,.0f} samples à générer ({hz} Hz, 24h)")

        while sim_s < day_s and not self._stop.is_set():
            intensity, profile = self._get_state_at(sim_s)

            if profile and intensity > 0.001:
                self.sensor.set_intensity(intensity, profile)
                label = f"{profile.name}  i={intensity:.2f}"
            else:
                self.sensor.set_idle()
                label = "idle"

            if label != self._current_state:
                h = int(sim_s // 3600)
                m = int((sim_s % 3600) // 60)
                print(f"[PRODUCER] {h:02d}h{m:02d} → {label}")
                self._current_state = label

            ax, ay, az, gx, gy, gz = self.sensor.read(sim_s)
            # ms_offset = millisecondes depuis minuit (relatif au timestamp du auth_frame)
            # Le backend recalcule : offsetMs - lastEntry + timestamp = position absolue
            ms_offset = int(sim_s * 1000)
            self.queue.push(Sample(ms_offset, ax, ay, az, gx, gy, gz))
            self._total_produced += 1
            sim_s += period_s

            if sleep_s > 0:
                time.sleep(sleep_s)

        print(f"[PRODUCER] Terminé — {self._total_produced:,} samples produits")

        # Attendre que le sender vide la queue avant de signaler la fin
        while len(self.queue) > 0 and not self._stop.is_set():
            time.sleep(0.05)
        self._stop.set()

    def _handshake(self) -> None:
        print("[HANDSHAKE] Attente du serveur...")
        resp = self.client.recv_until_newline()
        if not resp.startswith(b"OK"):
            raise RuntimeError(f"Handshake échoué (greeting): {resp!r}")
        print("[HANDSHAKE] Envoi du timestamp frame (minuit de la date simulée)...")
        self.client.sendall(encode_auth_frame(timestamp_ms=self.day_start_ms))
        resp = self.client.recv_until_newline()
        if not resp.startswith(b"OK"):
            raise RuntimeError(f"Handshake échoué (auth): {resp!r}")
        print("[HANDSHAKE] Authentification réussie!")

    def _connect_loop(self) -> None:
        attempt = 0
        while not self._stop.is_set():
            attempt += 1
            try:
                print(f"[CONNECTION] Tentative #{attempt}")
                self.client.connect()
                self._handshake()
                print("[CONNECTION] Prêt à streamer.")
                return
            except Exception as e:
                self.client.close()
                print(f"[CONNECTION] Échec: {e} — retry dans {self.args.reconnect_backoff}s")
                time.sleep(self.args.reconnect_backoff)

    def _sender(self) -> None:
        # Taille du buffer backend : 28*1000 bytes, chaque frame = 29 bytes
        # → 965 samples par buffer. On envoie par batch de 25 (comme le vrai Pi
        #   à 50 Hz avec send_loop_sleep_s=0.5s) pour éviter les micro-documents
        #   résiduels causés par des rafales trop grandes.
        batch_size = self.args.batch_size
        while not self._stop.is_set() or len(self.queue) > 0:
            if self.client.sock is None:
                self._connect_loop()
            try:
                frames = bytearray()
                count = 0
                while len(self.queue) > 0 and count < batch_size:
                    s = self.queue.pop()
                    if s:
                        frames += encode_single_frame(s)
                        self._total_sent += 1
                        count += 1
                if frames:
                    self.client.sendall(bytes(frames))
                    if not math.isinf(self.speed_factor):
                        # En mode ralenti, respecter le rythme du vrai Pi
                        time.sleep(batch_size / max(1, self.args.hz) / self.speed_factor)
                else:
                    time.sleep(0.005)
            except Exception as e:
                print(f"[SENDER] Erreur: {e} — reconnexion dans {self.args.reconnect_backoff}s")
                self.client.close()
                time.sleep(self.args.reconnect_backoff)

    def _stats_reporter(self) -> None:
        day_s = 24 * 3600
        while not self._stop.is_set():
            time.sleep(10)
            sim_s = self._total_produced / max(1, self.args.hz)
            pct   = sim_s / day_s * 100
            print(
                f"[STATS] Simulé: {sim_s/3600:.2f}h/24h ({pct:.1f}%)  |  "
                f"Produit: {self._total_produced:,}  |  "
                f"Envoyé: {self._total_sent:,}  |  "
                f"Queue: {len(self.queue):,}"
            )

    def run(self) -> None:
        speed_label = "fast (max)" if math.isinf(self.speed_factor) else f"{self.speed_factor}x"
        print("=" * 65)
        print("  WearPark Neurological Simulator")
        print("=" * 65)
        print(f"  Date simulée : {self.args.date}  (minuit UTC = {self.day_start_ms} ms)")
        print(f"  Attaques     : {self.args.attacks}")
        print(f"  Type         : {self.args.tremor_type}")
        print(f"  Fréquence    : {self.args.hz} Hz")
        print(f"  Vitesse      : {speed_label}")
        print(f"  Serveur      : {self.args.host}:{self.args.port}")
        print(f"  TLS          : {'activé' if self.args.tls else 'désactivé'}")
        if self.args.seed is not None:
            print(f"  Seed         : {self.args.seed}  (reproductible)")

        self._print_schedule()

        threading.Thread(target=self._producer,       daemon=True).start()
        threading.Thread(target=self._stats_reporter, daemon=True).start()

        try:
            self._sender()
        except KeyboardInterrupt:
            print("\n[SIM] Interrompu par l'utilisateur.")
        finally:
            self._stop.set()
            self.client.close()
            print(
                f"\n[SIM] Terminé.  "
                f"Produit: {self._total_produced:,}  |  "
                f"Envoyé: {self._total_sent:,}"
            )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="WearPark — Simulateur neurologique (tremblements de poignet)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # 5 attaques aléatoires, les deux types, mode fast
  python simulator.py --date 2024-03-15 --attacks 5

  # Parkinson uniquement, 3 attaques, reproductible
  python simulator.py --date 2024-03-15 --attacks 3 --tremor-type parkinson --seed 42

  # Temps réel (pour tester le flux en conditions réelles)
  python simulator.py --date 2024-03-15 --attacks 4 --speed realtime

  # 60x plus vite que le temps réel
  python simulator.py --date 2024-03-15 --attacks 6 --speed 60

  # 100 Hz, essentiel, avec TLS
  python simulator.py --date 2024-03-15 --attacks 4 --hz 100 \\
      --tremor-type essential --tls --ca-cert ca.pem
        """,
    )

    # Paramètres principaux
    p.add_argument("--date", required=True,
                   help="Date simulée YYYY-MM-DD  (ex: 2024-03-15)")
    p.add_argument("--attacks", type=int, default=4,
                   help="Nombre d'épisodes dans la journée  (défaut: 4)")
    p.add_argument("--tremor-type", dest="tremor_type",
                   choices=["parkinson", "essential", "both"], default="both",
                   help="Type de tremblement  (défaut: both)")
    p.add_argument("--hz", type=int, default=50,
                   help="Fréquence d'échantillonnage en Hz  (défaut: 50)")
    p.add_argument("--seed", type=int, default=None,
                   help="Graine aléatoire pour reproductibilité  (défaut: aléatoire)")

    # Vitesse
    p.add_argument("--speed", default="fast",
                   help="'fast' | 'realtime' | facteur numérique (ex: 60)  (défaut: fast)")

    # Réseau
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--batch-size", type=int, default=25, dest="batch_size",
                   help="Samples par batch TCP (défaut: 25, comme le vrai Pi à 50Hz)")
    p.add_argument("--reconnect-backoff", type=float, default=2.0,  dest="reconnect_backoff")
    p.add_argument("--connect-timeout",   type=float, default=5.0,  dest="connect_timeout")
    p.add_argument("--io-timeout",        type=float, default=30.0, dest="io_timeout")

    # TLS
    p.add_argument("--tls",         action="store_true")
    p.add_argument("--ca-cert",     default="", dest="ca_cert")
    p.add_argument("--client-cert", default="", dest="client_cert")
    p.add_argument("--client-key",  default="", dest="client_key")

    return p.parse_args()


if __name__ == "__main__":
    NeurologicalSimulator(parse_args()).run()