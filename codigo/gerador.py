# Everton - 288 medicoes por sensor, totalizando 1728.
from datetime import datetime, timedelta, timezone
import random
from pymongo import ReplaceOne

INICIO = datetime(2026, 10, 20, tzinfo=timezone.utc)
FIM = INICIO + timedelta(hours=24)


def gerar(sensores):
    randomico = random.Random(42)
    medicoes = []
    for sensor in sensores:
        for i in range(288):
            medicao = {
                '_id': 'etapa1:%s:%03d' % (sensor['_id'], i),
                'sensor_id': sensor['_id'],
                'timestamp': INICIO + timedelta(minutes=i*5),
                'pm25': round(randomico.uniform(10, 40), 2),
                'pm10': round(randomico.uniform(20, 70), 2),
                'co2': randomico.randint(400, 700),
                'temperatura': round(randomico.uniform(20, 30), 2),
                'umidade': round(randomico.uniform(50, 80), 2)}
            medicoes.append(medicao)
    return medicoes


def inserir(db, medicoes):
    operacoes = []
    for medicao in medicoes:
        operacao = ReplaceOne({'_id': medicao['_id']}, medicao, upsert=True)
        operacoes.append(operacao)
    db.Medicoes.bulk_write(operacoes)
