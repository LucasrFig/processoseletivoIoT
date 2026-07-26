from machine import Pin, I2C
from time import sleep, ticks_ms, ticks_diff

# Constantes e Parametrizações =========================================================

LIMITE_TEMPO_X = 5000       # Tempo limite de porta aberta (5000 ms = 5s)
LIMITE_VARIACAO_Y = 3.0     # Variação máxima de temperatura (em °C)
ATRASO_NORMALIZACAO = 1000  # Tempo estabilização para o CI (1000 ms = 1s)

MPU_ADDR = 0x68             # Endereço I2C padrão do MPU6050
PWR_MGMT_1 = 0x6B           # Registrador de energia
TEMP_OUT0 = 0x41            # Registrador de leitura da temperatura

PINO_BOTAO = 4              # Pino do botão (btn1)
PINO_SCL = 22               # Pino SCL do I2C
PINO_SDA = 21               # Pino SDA do I2C


# Funções Auxiliares =========================================================
def signedIntFromBytes(x, endian="big"):
    y = int.from_bytes(x, endian)
    if y >= 0x8000:
        return -((65535 - y) + 1)
    else:
        return y


def ler_temperatura(i2c_bus):
    try:
        raw_data = i2c_bus.readfrom_mem(MPU_ADDR, TEMP_OUT0, 2)
        raw_temp = signedIntFromBytes(raw_data, "big")
        return (raw_temp / 340.0) + 36.53
    except Exception:
        return float("NaN")

# Configuração do Hardware =========================================================


botao = Pin(PINO_BOTAO, Pin.IN, Pin.PULL_DOWN)
i2c = I2C(0, scl=Pin(PINO_SCL), sda=Pin(PINO_SDA))

try:
    i2c.writeto_mem(MPU_ADDR, PWR_MGMT_1, b'\x00')
    sleep(0.1)
except Exception:
    pass

# Inicialização do Sistema (Bloqueio de Segurança) =========================================================
temp_referencia = None
while temp_referencia is None:
    t = ler_temperatura(i2c)
    if t == t:  # Verifica se a leitura é um número válido
        temp_referencia = t
    sleep(0.05)

print("Sistema de Monitoramento Inicializado")

tempo_abertura_inicio = None
tempo_normalizacao = None
alarme_porta_ativo = False
alarme_temp_ativo = False

# Loop Principal =========================================================
while True:
    estado_porta = botao.value()
    temperatura_atual = ler_temperatura(i2c)

    # Lógica de Tempo de Porta Aberta -----------------------------------------------------
    # Verifica se está aberta e quanto tempo se passou:

    if estado_porta == 0:
        if tempo_abertura_inicio is None:
            tempo_abertura_inicio = ticks_ms()
        else:
            tempo_decorrido = ticks_diff(ticks_ms(), tempo_abertura_inicio)
            if tempo_decorrido >= LIMITE_TEMPO_X and not alarme_porta_ativo:
                alarme_porta_ativo = True
                # Caso ultrapasse 5 segund aberta
                print("ALERTA: Porta aberta por muito tempo!")
    else:
        tempo_abertura_inicio = None

    # Lógica de Elevação Térmica -----------------------------------------------------
    # Verifica se é a primeira temperatura registrada e a guarda,
    # caso haja uma mudança de temperatura abrupta de mais de 3°C ele emite o alerta:

    if temperatura_atual == temperatura_atual:
        delta_t = temperatura_atual - temp_referencia

        # 1.Verifica se houve salto térmico
        if delta_t >= LIMITE_VARIACAO_Y and not alarme_temp_ativo:
            alarme_temp_ativo = True
            print("ALERTA: Degradacao termica detectada!")

        # 2.Se não há alarme e a porta está fechada, acompanha a temperatura ambiente (ex: descer pra 20C)
        elif not alarme_temp_ativo and estado_porta == 1:
            temp_referencia = temperatura_atual

    # D. Lógica de Normalização -----------------------------------------------------
    # Quando a temperatura estabiliza novamente e a porta é fechada
    # o programa aguarda 1 segundo para confirmar a normalização pelo terminal:

    if alarme_porta_ativo or alarme_temp_ativo:
        condicao_porta_ok = (estado_porta == 1)
        condicao_temp_ok = (
            (temperatura_atual - temp_referencia) < LIMITE_VARIACAO_Y)

        if condicao_porta_ok and condicao_temp_ok:
            if tempo_normalizacao is None:
                tempo_normalizacao = ticks_ms()
            elif ticks_diff(ticks_ms(), tempo_normalizacao) >= ATRASO_NORMALIZACAO:
                alarme_porta_ativo = False
                alarme_temp_ativo = False
                temp_referencia = temperatura_atual
                tempo_normalizacao = None
                print("Status: Sistema Normalizado.")
        else:
            tempo_normalizacao = None

    sleep(0.05)  # Sleep Entre cada interação
