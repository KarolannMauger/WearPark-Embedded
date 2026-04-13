python simulator.py --date 2026-03-29 --speed realtime --tremor-type parkinson --attacks 5 --tls --hz 100 --client-cert certs/devices/device-test/client.crt --client-key certs/devices/device-test/client.key

python simulator.py --date 2026-03-29 --tremor-type parkinson --attacks 5 --tls --hz 100 --client-cert certs/devices/device-test/client.crt --client-key certs/devices/device-test/client.key


# Cas typique
python simulator.py --date 2024-03-15 --attacks 5

# Parkinson uniquement, reproductible (même seed = même journée)
python simulator.py --date 2024-03-15 --attacks 3 --tremor-type parkinson --seed 42

# 60x plus vite que le temps réel
python simulator.py --date 2024-03-15 --attacks 4 --speed 60

# Mode temps réel (pour tester le flux en conditions réelles)
python simulator.py --date 2024-03-15 --attacks 4 --speed realtime

# option batch-size
--batch-size 10