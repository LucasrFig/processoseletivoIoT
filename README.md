# Processo Seletivo – Intensivo Maker | IoT

---

## Relatório do Candidato

### Identificação do Candidato

- **Nome completo:** Lucas Ricardo de Lima Figueiredo
- **GitHub:** https://github.com/LucasrFig 

---

## Visão Geral da Solução

O objetivo do projeto é criar um sistema que monitore ambientes sensíveis (Ex: Refrigeradores, estufas, laboratórios, etc.). O sistema embarcado deve gerar alertas para as seguintes situações:
- Grandes mudanças na temperatura
- Porta aberta por mais de 5 segundos
  
Na simulação, a abertura da porta é representada por um botão. Se estiver pressionado, a porta está fechada; se estiver solto, a porta está aberta. Caso o botão permaneça solto por mais de 5 segundos, uma mensagem é apresentada no terminal informando que a porta está aberta há muito tempo. 

O sensor de temperatura utilizado na simulação é o MPU6050. No início do programa, é salva a temperatura base com a porta fechada. A partir desse momento, o sistema monitora a variação da temperatura constantemente. Caso identifique uma variação além do limite estabelecido, o microcontrolador apresenta uma mensagem alertando sobre a degradação térmica.

As únicas interações da simulação com o usuário são o pressionar do botão (simulando o fechamento e a abertura da porta) e a alteração do valor do sensor de temperatura. A resposta do sistema sempre se dará através de mensagens no terminal.

---

## Arquitetura do Sistema Embarcado

O sistema foi construído com uma arquitetura de laço de repetição contínuo com gestão de estados não-bloqueante. Isso garante que o microcontrolador consiga monitorar múltiplos sensores simultaneamente sem que um atrase o outro.

### Diagrama de Fluxo Simplificado

```text
[Ligar/Reset] 
      │
      ⬇
(Setup de Hardware) ──> Configura Pinos do botão e Barramento I2C (MPU6050)
      │
      ⬇
(Bloqueio de Segurança) ──> Para aguardar o sensor estabilizar e captura a Temperatura Base Inicial
      │
      ⬇
[Loop Principal de Monitoramento]
      │
      ├──> 1. Ler Sensores: Captura estado da porta e temperatura atual.
      │
      ├──> 2. Lógica da Porta: Porta aberta? 
      │       ├── Sim: Conta tempo. Passou de 5s? -> DISPARA ALARME PORTA.
      │       └── Não: Zera cronômetro da porta.
      │
      ├──> 3. Lógica Térmica: Variação de temperatura >= 3°C?
      │       ├── Sim: -> DISPARA ALARME TÉRMICO.
      │       └── Não: Se porta fechada, atualiza temperatura base (adaptação ao ambiente).
      │
      └──> 4. Normalização: O sistema estava em alarme?
              ├── Sim: Condições estão seguras há mais de 1 segundo? -> ZERA ALARMES. 
              └── Não: Mantém estado atual.
```

### Interação entre Componentes
A comunicação entre o hardware e o software acontece de duas formas distintas:
* **Entrada Digital (Botão/Porta):** O pino do botão é configurado com um resistor interno de `PULL_DOWN`. Quando a porta está fechada, o circuito é ativado, enviando nível lógico `1`. Quando aberta, envia `0`.
* **Comunicação I2C (Sensor MPU6050):** O ESP32 atua como *Mestre* no barramento I2C, enviando requisições aos registradores de memória do sensor (endereço `0x68`) para ler os bytes brutos do termômetro embutido, que são então convertidos para graus Celsius via software.

### Fluxo Principal do Programa `main.py`
O código está dividido em duas fases principais:
1. **Fase de Inicialização (Setup):** O microcontrolador acorda os periféricos e entra em uma barreira de segurança `while temp_referencia is None`. O sistema se recusa a iniciar o monitoramento até que o sensor I2C retorne uma leitura real e válida, evitando falsos positivos causados pelo atraso de inicialização do hardware.
2. **Fase de Execução (Main Loop):** Um laço `while True` que atua como o coração do sistema, rodando ininterruptamente para ler as variáveis e enviar as mensagens para o terminal, caso necessário.

### Gestão de Estados e Temporização
O projeto evita propositalmente o uso de funções bloqueantes, como longos `sleep()`, para a gestão dos alarmes. Em vez disso, utiliza a contagem de tempo do processador `ticks_ms` para gerenciar eventos simultâneos:

* **Concorrência:** Ao salvar a "marca temporal" de quando a porta foi aberta (`tempo_abertura_inicio`), o sistema subtrai esse valor do tempo atual para saber quantos milissegundos se passaram. Isso permite que o ESP32 continue monitorando a temperatura enquanto o tempo da porta esgota.
* **Referência Adaptativa:** A temperatura não é comparada a um valor fixo, mas sim a uma `temp_referencia` dinâmica. Se o ambiente esfriar naturalmente, o sistema atualiza essa referência. O alarme só soa em caso de saltos bruscos.
* **Debounce de Normalização:** Para evitar que o sistema declare normalização falsa (ex: uma batida rápida na porta), foi implementada uma trava de tempo. O sistema só se declara normalizado e limpa as variáveis de erro se as leituras físicas se mantiverem seguras por um tempo contínuo predeterminado (1000 ms).
* **Pausa do Processador:** Um pequeno `sleep(0.05)` no final do loop garante que o processador pare por um momento, economizando energia e garantindo a estabilidade da leitura do sensor sem engasgos.
---

## Componentes Utilizados na Simulação

O hardware virtual foi montado no simulador Wokwi utilizando os seguintes componentes (mapeados no arquivo `diagram.json`):

* **Microcontrolador (ESP32 DevKit V4):**
  * **Função:** Atua como o cérebro central do sistema. Roda o firmware em MicroPython, gerencia o relógio interno para a temporização, processa as leituras periféricas e executa a máquina de estados que dispara ou silencia os alarmes via terminal.
    
<div align="center">
  <img width="412" height="396" alt="image" src="https://github.com/user-attachments/assets/0da6585f-feaf-44f5-8c36-65b318b397f4" />
</div>

* **Sensor MPU6050 (Módulo I2C):**
  * **Função:** Além de ser um giroscópio e acelerômetro de 6 eixos, neste projeto ele é utilizado especificamente para explorar o seu **termômetro digital interno**. Ele se comunica com o ESP32 através do protocolo I2C (Pinos SDA 21 e SCL 22), fornecendo as leituras brutas necessárias para o cálculo do gradiente térmico.

<div align="center">
  <img width="447" height="406" alt="image" src="https://github.com/user-attachments/assets/1d9446c3-a62a-4a24-8f9c-443df58d3643" />
</div>

* **Botão (Pushbutton - `btn1`):**
  * **Função:** Simula o comportamento de um interruptor magnético ou "chave fim de curso" acoplada à porta ou tampa do compartimento monitorado. Ligado ao pino 4 (com resistor de `PULL_DOWN` interno), ele injeta nível lógico `1` quando pressionado (simulando a porta fechada/vedada) e nível lógico `0` quando solto (iniciando a contagem de violação de exposição).

<div align="center">
  <img width="436" height="389" alt="image" src="https://github.com/user-attachments/assets/24832004-0ef7-444d-a0d2-07c6f3f20674" />
</div>

---

## Decisões Técnicas Relevantes
  
As decisões de arquitetura foram:

* **Parametrização Centralizada:** A definição de limites críticos no início do arquivo (como `LIMITE_TEMPO_X` e `LIMITE_VARIACAO_Y` configurados em constantes) evita codar os valores diretamente no código. Isso permite que os parâmetros do sistema sejam ajustados rapidamente para diferentes ambientes de negócio sem alterar a estrutura da lógica principal.
* **Temporização Não-Bloqueante:** Para permitir a concorrência real das tarefas, o controle de tempo foi feito utilizando `ticks_ms()` e `ticks_diff()`. O uso do `sleep()` foi evitado na contagem de alarmes para garantir que o microcontrolador monitore a temperatura e o estado da porta simultaneamente, sem interrupções.
* **Máquina de Estados Simples:** A utilização de `flags` de estado, como `alarme_porta_ativo` e `alarme_temp_ativo`, garante que o sistema atue por gatilhos de transição. Isso impede que o terminal seja inundado com alertas repetidos enquanto a condição de falha persistir.
* **Tratamento de Hardware e *Debounce*:**
  * **Wake-up do Sensor:** Adição de um bloqueio lógico na inicialização para garantir que o sistema só inicie após o MPU6050 estabilizar.
  * **Debounce de Normalização:** Implementação de uma trava de tempo (`ATRASO_NORMALIZACAO`) que exige 1 segundo contínuo de leituras seguras antes de declarar a normalização, mitigando falsos positivos causados por oscilações mecânicas da porta.
* **Referência Térmica Adaptativa:** A captura de temperatura não é comparada a um teto fixo. A variável `temp_referencia` foi desenhada para acompanhar o resfriamento natural do ambiente, disparando o alarme apenas caso ocorra o salto térmico brusco.
---

## Resultados Obtidos

### Requisitos atendidos:
De modo geral, o sistema atende aos requisitos do processo seletivo:
- A porta não pode ficar aberta por mais de 5 segundos, senão, o alerta é disparado. Caso ela se feche, o sistema registra que a porta está em estado normal.
- A temperatura não pode sofrer elevações abruptas, senão, o alerta é disparado. Caso ela volte ao nível estável, o sistema  registra que a temperatura está em um nível normal.
- Caso ambas estejam em estado normal, e isso se mantenha durante 1 segundo, o sistema informa a normalização (Para evitar falsas leituras: como a porta batendo e abrindo novamente ou a temperatura oscilando demais).

### Simulação do Wokwi
<div align="center">
<img width="439" height="386" alt="image" src="https://github.com/user-attachments/assets/3042be84-535b-4a71-b947-1ec63e607ef0" />
</div>

A simulação funcionou corretamente, todas as mensagens solicitadas no README.md do projeto foram apresentadas no momento certo. Nenhum problema de interação com a simulação.

---

## Comentários Adicionais (Opcional)

Primeiramente queria falar dos aprendizados. Pela primeira vez programei em MicroPython, já tinha tido contato durante os cursos, mas montar o projeto inteiro em MicroPython foi uma experiência interessante. Implementar diretamente a leitura do dispositivo `MPU6050` foi um desafio, não quis usar a biblioteca inteira do `MPU6050` somente para usar a função de ler temperatura, fui atrás de outros repositórios que implementavam esse processo de leitura via I2C e utilizei o que aprendi na função `ler_temperatura()` em meu código.

Quanto a melhorias, eu não tive muito tempo para me dedicar aos projetos do processo seletivo com mais persistência devido a outros projetos pessoais concomitantes, mas com mais tempo eu com certeza adicionaria um sistema de histórico à solução, com registros de tempo automáticos de cada evento (Porta aberta, Porta fechada, Pico de temperatura), desse modo é muito mais fácil para um ser humano monitorar a operação do sistema embarcado. Outra adição interessante é o registro da temperatura do ambiente ao longo do tempo.


---

## Especificação dos Testes Automatizados (Wokwi CI)

Para que o projeto seja validado com sucesso na esteira de integração contínua (CI), o firmware escrito em MicroPython deve interagir corretamente com as leituras dos sensores descritos em cada cenário e enviar as mensagens de status exatas.

### Requisitos Críticos de Implementação

1. **Casamento Exato de Strings:** O Wokwi CI faz uma verificação estrita caractere por caractere. Se houver divergência em maiúsculas/minúsculas, acentuação ou falta de pontuação, o teste irá falhar.
2. **Arquitetura Não-Bloqueante:** Evite o uso de funções bloqueantes. Elas podem fazer com que o firmware perca a janela de tempo em que o simulador altera o peso, quebrando a sincronia do teste automatizado.

---

## Suporte

Em caso de dúvidas:

- Consulte o material dos cursos EAD
- Leia atentamente este README
- Analise os logs das GitHub Actions
- Utilize os canais oficiais para contato com os instrutores
