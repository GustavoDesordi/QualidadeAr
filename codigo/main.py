# Demonstracao das quatro partes, executada pelo console.
from datetime import timedelta
from pprint import pprint
import banco
import gerador
import consultas
import agregacoes
import redis_service


def main():
    cliente, db = banco.conectar()
    try:
        print('\n1. ARIEL - MongoDB e modelagem')
        sensores = banco.cadastrar(db)
        pprint(sensores)

        print('\n2. EVERTON - Simulador')
        medicoes = gerador.gerar(sensores)
        gerador.inserir(db, medicoes)
        print('Medicoes geradas:', len(medicoes))
        print('Medicoes no MongoDB:', db.Medicoes.count_documents({}))
        print('Consulta de S001, das 10h as 11h UTC:')
        inicio = gerador.INICIO + timedelta(hours=10)
        resultado = consultas.consultar(db, 'S001', inicio, inicio+timedelta(hours=1))
        print('Quantidade:', len(resultado))
        pprint(resultado[:2])

        print('\n3. GUSTAVO - Agregacoes')
        por_sensor = agregacoes.resumir(db, gerador.INICIO, gerador.FIM, 'sensor')
        por_cidade = agregacoes.resumir(db, gerador.INICIO, gerador.FIM, 'cidade')
        print('Resumos por sensor:', len(por_sensor))
        print('Resumos por cidade:', len(por_cidade))
        pprint(por_sensor[0])
        pprint(por_cidade[0])

        print('\n4. LUIZ - Redis e integracao')
        cache = redis_service.conectar()
        try:
            chaves = redis_service.salvar(cache, por_sensor+por_cidade)
            print('Hashes gravados:', len(chaves))
            for nome in sorted(chaves):
                print('\nHGETALL', nome)
                pprint(redis_service.consultar(cache, nome))
        finally:
            cache.close()
    finally:
        cliente.close()


if __name__ == '__main__':
    main()
