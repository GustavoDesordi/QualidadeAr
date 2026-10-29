# Ariel - conexao, cadastro e indice do MongoDB.
from pymongo import MongoClient


def conectar():
    cliente = MongoClient('mongodb://localhost:27017/', tz_aware=True,
                          serverSelectionTimeoutMS=3000)
    cliente.admin.command('ping')
    return cliente, cliente['QualidadeAr']


def cadastrar(db):
    cidades = [('Chapecó', -27.1009, -52.6157),
               ('Xanxerê', -26.8760, -52.4040),
               ('Concórdia', -27.2340, -52.0270)]
    sensores = []
    for i in range(6):
        cidade, latitude, longitude = cidades[i // 2]
        sensor = {
            '_id': 'S%03d' % (i + 1), 'modelo': 'AirMonitor-200',
            'descricao': 'Sensor ambiental de ' + cidade,
            'localizacao': {'cidade': cidade, 'uf': 'SC',
                            'latitude': latitude, 'longitude': longitude},
            'ativo': True,
            'grandezas': ['PM2.5', 'PM10', 'CO2', 'temperatura', 'umidade']}
        sensores.append(sensor)
        db.Sensores.replace_one({'_id': sensor['_id']}, sensor, upsert=True)
    db.Medicoes.create_index([('sensor_id', 1), ('timestamp', -1)], unique=True)
    return sensores
