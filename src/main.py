from machine import Pin, I2C
from time import sleep, ticks_ms, ticks_diff

# =========================================================
# 1. Constantes e Parametrizações
# =========================================================
LIMITE_TEMPO_X = 5000       # Tempo limite de porta aberta (5000 ms = 5s)
LIMITE_VARIACAO_Y = 3.0     # Variação máxima de temperatura (Delta T em °C)

MPU_ADDR = 0x68             # Endereço I2C padrão do MPU6050
PWR_MGMT_1 = 0x6B           # Registrador de energia
TEMP_OUT0 = 0x41            # Registrador de leitura da temperatura

PINO_BOTAO = 4              # Pino do botão (btn1)
PINO_SCL = 22               # Pino SCL do I2C
PINO_SDA = 21               # Pino SDA do I2C

# =========================================================
# 2. Funções Auxiliares
# =========================================================
def signedIntFromBytes(x, endian="big"):
    """ Converte bytes brutos do I2C para inteiro com sinal """
    y = int.from_bytes(x, endian)
    if y >= 0x8000:
        return -((65535 - y) + 1)
    else:
        return y

def ler_temperatura(i2c_bus):
    """ Lê a temperatura atual do sensor MPU6050 """
    try:
        raw_data = i2c_bus.readfrom_mem(MPU_ADDR, TEMP_OUT0, 2)
        raw_temp = signedIntFromBytes(raw_data, "big")
        return (raw_temp / 340.0) + 36.53
    except Exception:
        return float("NaN")

# =========================================================
# 3. Configuração do Hardware
# =========================================================
# Botão btn1: 1 = Pressionado/Fechado, 0 = Solto/Aberto
botao = Pin(PINO_BOTAO, Pin.IN, Pin.PULL_DOWN)

# Comunicação I2C
i2c = I2C(0, scl=Pin(PINO_SCL), sda=Pin(PINO_SDA))

# Acorda o MPU6050
try:
    i2c.writeto_mem(MPU_ADDR, PWR_MGMT_1, b'\x00')
    sleep(0.1)
except Exception:
    pass

# =========================================================
# 4. Inicialização do Sistema (Item A do Escopo)
# =========================================================
print("Sistema de Monitoramento Inicializado")

# Variáveis de Estado
tempo_abertura_inicio = None
temp_referencia = None

alarme_porta_ativo = False
alarme_temp_ativo = False

# =========================================================
# 5. Loop Principal
# =========================================================
while True:
    estado_porta = botao.value()  # 1 = Fechada, 0 = Aberta
    temperatura_atual = ler_temperatura(i2c)

    # Define a temperatura de referência inicial se ainda não estiver definida
    if temp_referencia is None and temperatura_atual == temperatura_atual: # (Garante que não é NaN)
        temp_referencia = temperatura_atual

    # -----------------------------------------------------
    # B. Lógica de Tempo de Porta Aberta (Limite X)
    # -----------------------------------------------------
    if estado_porta == 0:  # Porta Solta / Aberta
        if tempo_abertura_inicio is None:
            tempo_abertura_inicio = ticks_ms()
        else:
            tempo_decorrido = ticks_diff(ticks_ms(), tempo_abertura_inicio)
            if tempo_decorrido >= LIMITE_TEMPO_X and not alarme_porta_ativo:
                alarme_porta_ativo = True
                print("ALERTA: Porta aberta por muito tempo!")
    else:  # Porta Pressionada / Fechada
        tempo_abertura_inicio = None

    # -----------------------------------------------------
    # C. Lógica de Elevação Térmica (Variação Y)
    # -----------------------------------------------------
    if temp_referencia is not None and temperatura_atual == temperatura_atual:
        # Atualiza a referência continuamente enquanto a porta estiver fechada e sem alarme térmico
        if estado_porta == 1 and not alarme_temp_ativo:
            temp_referencia = temperatura_atual

        delta_t = temperatura_atual - temp_referencia

        if delta_t >= LIMITE_VARIACAO_Y and not alarme_temp_ativo:
            alarme_temp_ativo = True
            print("ALERTA: Degradacao termica detectada!")

    # -----------------------------------------------------
    # D. Lógica de Normalização e Restauração de Estado
    # -----------------------------------------------------
    # Se o sistema estava em alarme e AMBAS as condições voltaram aos limites seguros
    if alarme_porta_ativo or alarme_temp_ativo:
        condicao_porta_ok = (estado_porta == 1)
        condicao_temp_ok = (temp_referencia is not None and (temperatura_atual - temp_referencia) < LIMITE_VARIACAO_Y)

        if condicao_porta_ok and condicao_temp_ok:
            alarme_porta_ativo = False
            alarme_temp_ativo = False
            # Atualiza a referência de temperatura para a nova condição normalizada
            temp_referencia = temperatura_atual
            print("Status: Sistema Normalizado.")

    # Pequena pausa não-bloqueante de 50ms para precisão de tempo do CI
    sleep(0.05)