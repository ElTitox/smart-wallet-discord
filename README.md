<details>
<summary><b>🇪🇸 Leer en Español</b></summary>

# Smart Wallet — Edición Discord 💼🤖

Un bot asistente financiero para Discord impulsado por la **API de Google Gemini**, **SQLite** y **yfinance**. Ayuda a estudiantes y usuarios a registrar gastos personales, simular inversiones, calcular impuestos (como el ITBMS en Panamá) y consultar precios de acciones y criptomonedas en tiempo real, todo directamente desde Discord.

---

## 📜 Agradecimientos y Atribución

Este proyecto es un **fork adaptado a Discord** del agente original **Smart Wallet** diseñado para Telegram por **Isaías Reyes**.

> **Repositorio Original:** [github.com/Isaiasr26/contecs-2026-smart-wallet](https://github.com/Isaiasr26/contecs-2026-smart-wallet)  
> **Autor Original:** Isaías Reyes ([github.com/Isaiasr26](https://github.com/Isaiasr26))

### 💡 Sobre este Fork
Esta versión fue construida tras participar en el taller interactivo **"Más allá del Chatbot: Construyendo Agentes con Tool Calling y Automatización de Procesos"** dictado por Isaías Reyes en **CONTECS 2026** (Facultad de Ingeniería de Sistemas Computacionales - FISC, Universidad Tecnológica de Panamá) el 20 de octubre de 2026.

¡Un agradecimiento especial a Isaías Reyes por compartir su arquitectura de agente financiero y la lógica de llamadas a funciones (tool calling), la cual inspiró esta adaptación de Telegram a Discord!

---

## ✨ Características

- **Registro Automatizado de Gastos e Ingresos:** Registra transacciones utilizando lenguaje natural (ej. *"Gasté $6.50 en el almuerzo"* o *"Recibí la beca de $300"*).
- **Persistencia con Base de Datos SQLite:** Las transacciones se guardan de forma segura en la base de datos local `smart_wallet.db`.
- **Cálculos Financieros:** Uso nativo de herramientas (*tool calling*) para el cálculo del impuesto ITBMS y simulación de inversiones con interés compuesto.
- **Datos del Mercado:** Consulta precios de acciones y criptomonedas en tiempo real a través de `yfinance`.
- **Dos Modos de Ejecución:**
  - `financebot.py` *(Recomendado)*: Incluye un **Motor de Fallback de Modelos** automático que conmuta entre modelos Gemini de respaldo cuando ocurre un límite de tasa (429), alta demanda (503) o endpoint no disponible (404).
  - `financebot_simple.py`: Una versión ligera de un solo modelo, ideal para pruebas y referencia educativa.

---

## 🛠️ Herramientas Disponibles del Agente

El agente utiliza las siguientes funciones nativas de Python a través de Gemini Function Calling:

| Herramienta | Descripción |
|---|---|
| `consultar_saldo_cuenta(cuenta)` | Devuelve el saldo de cuentas de prueba (`efectivo`, `banco`, `yappy`). |
| `registrar_movimiento(...)` | Guarda un ingreso o gasto en SQLite utilizando marcadores de posición (`?`). |
| `consultar_billetera()` | Consulta ingresos, gastos, saldo actual y actividad reciente en la base de datos. |
| `eliminar_movimiento(id)` | Elimina un movimiento específico según su ID. |
| `obtener_precio_activo(ticker)` | Obtiene cotizaciones en vivo de acciones o criptos vía `yfinance` con precios de respaldo. |
| `simular_inversion(...)` | Calcula el interés compuesto aplicando la fórmula financiera exacta. |
| `calcular_itbms_panama(...)` | Calcula el ITBMS de Panamá (7% general, 10% licor/hospedaje, 15% cigarrillos) y totales. |

---

## 🚀 Guía de Inicio Rápido

### 1. Requisitos Previos

Asegúrate de tener instalado en tu equipo:
- **Python 3.10+**
- **Git**
- Un **Bot Token de Discord** (desde el [Discord Developer Portal](https://discord.com/developers/applications))
- Una **API Key de Google Gemini** (desde [Google AI Studio](https://aistudio.google.com/apikey))

---

### 2. Instalación y Configuración del Entorno

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/ElTitox/smart-wallet-discord.git
   cd smart-wallet-discord
   ```

2. **Crear y activar un Entorno Virtual:**
   - **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD):**
     ```cmd
     python -m venv .venv
     .\.venv\Scripts\activate.bat
     ```
   - **Linux / macOS / Git Bash:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

---

### 3. Configuración de Claves de API

Crea tu archivo `.env` renombrando el archivo `secretkeys.example.py` (o creando uno nuevo desde cero en la raíz del proyecto) y configura tus credenciales:

```env
DISCORD_TOKEN=tu_discord_bot_token_aqui
GOOGLE_API_KEY=tu_gemini_api_key_aqui
```

### 4. Configuración en el Portal de Desarrolladores de Discord

1. Ve al [Discord Developer Portal](https://discord.com/developers/applications) y crea una **Nueva Aplicación**.
2. En la pestaña **Bot**:
   - Haz clic en **Reset Token** para copiar tu `DISCORD_TOKEN`.
   - Activa el **`MESSAGE CONTENT INTENT`** dentro de **Privileged Gateway Intents**.
3. En **OAuth2 -> URL Generator**:
   - Selecciona los permisos (*scopes*): `bot`.
   - Selecciona los permisos del bot: `Send Messages`, `Read Message History` y `Embed Links`.
   - Copia la URL generada e invita al bot a tu servidor de Discord.

---

### 5. Ejecutar el Bot

Ejecuta la versión con motor de degradación (*resilient*) desde tu terminal activada:

```bash
python financebot.py
```

*(Opcionalmente, ejecuta `python financebot_simple.py` para la versión básica de un solo modelo).*

#### Comandos en Discord:
- `!start` o `!ayuda`: Muestra el mensaje de bienvenida y ejemplos de uso.
- `!saldo`: Consulta directamente SQLite para mostrar saldo, total de ingresos y gastos.
- `!reset`: Reinicia la memoria de conversación del canal (las transacciones siguen guardadas en la base de datos).
- **Mensajes en lenguaje natural**: Escribe algo como *"Gasté $2.50 en el pasaje y $6.00 en el almuerzo"* para interactuar con el agente.

---

## ⚙️ Arquitectura y Secuencia de Degradación de Modelos (Fallback)

En `financebot.py`, para evitar caídas por límites de cuota de API o picos de alta demanda, el bot conmuta entre modelos en el siguiente orden de prioridad:

1. `gemini-3.5-flash` *(Principal)*
2. `gemini-3.1-flash-lite`
3. `gemini-3-flash`
4. `gemini-3.8-flash`

Si se detecta un error `429 (Límite de Cuota)`, `503 (Alta Demanda)` o `404 (No Encontrado)`, el bot migra automáticamente la sesión activa del canal al siguiente modelo disponible sin interrumpir la experiencia del usuario.

---

## 📄 Licencia y Descargo de Responsabilidad

Proyecto Educativo. Las respuestas del agente, los precios de mercado y las simulaciones de inversión **no constituyen asesoría financiera**.

Distribuido bajo la Licencia MIT.
</details>
<details open>
<summary><b>🇺🇸 Read in English</b></summary>

# Smart Wallet — Discord Edition 💼🤖

A financial assistant Discord bot powered by the **Google Gemini API**, **SQLite**, and **yfinance**. It helps students and individuals track personal expenses, simulate investments, calculate taxes (such as ITBMS in Panama), and query real-time stock and cryptocurrency prices—all directly within Discord.

---

## 📜 Acknowledgments & Attribution

This project is a **Discord-adapted fork** of the original **Smart Wallet** agent designed for Telegram by **Isaías Reyes**.

> **Original Repository:** [github.com/Isaiasr26/contecs-2026-smart-wallet](https://github.com/Isaiasr26/contecs-2026-smart-wallet)  
> **Original Author:** Isaías Reyes ([github.com/Isaiasr26](https://github.com/Isaiasr26))

### 💡 About This Fork
This version was built following the interactive workshop **"Más allá del Chatbot: Construyendo Agentes con Tool Calling y Automatización de Procesos"** presented by Isaías Reyes at **CONTECS 2026** (Facultad de Ingeniería de Sistemas Computacionales - FISC, Universidad Tecnológica de Panamá) on October 20, 2026.

Special thanks to Isaías Reyes for sharing his financial agent architecture and tool-calling logic, which inspired this adaptation from Telegram to Discord!

---

## ✨ Features

- **Automated Expense & Income Tracking:** Log transactions using natural language (e.g., *"I spent $6.50 on lunch"* or *"Received $300 scholarship"*).
- **SQLite Database Persistence:** Transactions are safely recorded in a local `smart_wallet.db` database.
- **Financial Calculations:** Native tool calling for ITBMS tax calculation and compound interest investment simulation.
- **Market Data:** Fetches real-time stock and cryptocurrency prices via `yfinance`.
- **Dual Script Modes:**
- `financebot.py` *(Recommended)*: Includes an automatic **Model Fallback Engine** that seamlessly switches through backup Gemini models when primary rate limits (429), high server demand (503), or unavailable endpoints (404) occur.
- `financebot_simple.py`: A lightweight, single-model version perfect for testing and educational reference.

---

## 🛠️ Available Agent Tools

The agent utilizes the following native Python functions via Gemini Function Calling:

| Tool | Description |
|---|---|
| `consultar_saldo_cuenta(cuenta)` | Returns balance for test accounts (`efectivo`, `banco`, `yappy`). |
| `registrar_movimiento(...)` | Records income or expenses directly into SQLite using placeholders (`?`). |
| `consultar_billetera()` | Queries database for income, expenses, current balance, and recent activity. |
| `eliminar_movimiento(id)` | Deletes a specific transaction by its ID. |
| `obtener_precio_activo(ticker)` | Fetches live stock/crypto quotes via `yfinance` with fallback data. |
| `simular_inversion(...)` | Calculates compound interest using exact financial formulas. |
| `calcular_itbms_panama(...)` | Calculates Panama's ITBMS tax (7% general, 10% alcohol/lodging, 15% tobacco). |

---

## 🚀 Quickstart Guide

### 1. Prerequisites

Make sure you have installed on your machine:
- **Python 3.10+**
- **Git**
- A **Discord Bot Token** (from the [Discord Developer Portal](https://discord.com/developers/applications))
- A **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/apikey))

---

### 2. Installation & Environment Setup

1. **Clone the repository:**
```bash
git clone https://github.com/ElTitox/smart-wallet-discord.git
cd smart-wallet-discord
```

2. **Create and activate a Virtual Environment:**
- **Windows (PowerShell):**
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```
- **Windows (CMD):**
    ```cmd
    python -m venv .venv
    .\.venv\Scripts\activate.bat
    ```
- **Linux / macOS / Git Bash:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

---

### 3. API Keys Configuration

Create your `.env` file by renaming the template file `secretkeys.example.py` (or creating a new one from scratch in the project root) and populate your credentials:

```env
DISCORD_TOKEN=your_discord_bot_token_here
GOOGLE_API_KEY=your_gemini_api_key_here
```

> ⚠️ **Security Note:** Never commit your `.env` or `secretkeys.py` file to GitHub. Verify that `.env` is listed inside your `.gitignore` file.

---

### 4. Discord Developer Portal Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications) and create a **New Application**.
2. Under the **Bot** tab:
- Click **Reset Token** to copy your `DISCORD_TOKEN`.
- Enable **`MESSAGE CONTENT INTENT`** under **Privileged Gateway Intents**.
3. Under **OAuth2 -> URL Generator**:
- Select scopes: `bot`.
- Select permissions: `Send Messages`, `Read Message History`, and `Embed Links`.
- Use the generated URL to invite the bot to your Discord server.

---

### 5. Running the Bot

Execute the resilient version from your activated terminal:

```bash
python financebot.py
```

*(Alternatively, run `python financebot_simple.py` for the basic single-model version).*

#### Discord Commands:
- `!start` or `!ayuda`: Displays the welcome message and examples.
- `!saldo`: Directly queries SQLite to display balance, total income, and expenses.
- `!reset`: Clears channel conversation memory (transactions remain saved in database).
- **Natural messages**: Simply type *"Spent $2.50 on the bus and $6.00 for lunch"* to interact with the AI agent.

---

## ⚙️ Architecture & Model Fallback Sequence

In `financebot.py`, to prevent downtime due to API rate limits or temporary server demand spikes, the bot cycles through models in the following priority order:

1. `gemini-3.5-flash` *(Primary)*
2. `gemini-3.1-flash-lite`
3. `gemini-3-flash`
4. `gemini-3.8-flash`

If a `429 (Quota Limit)`, `503 (High Demand)`, or `404 (Not Found)` error is encountered, the bot seamlessly migrates the channel's active session to the next available model without interrupting user experience.

---

## 📄 License & Disclaimer

Educational Project. The agent's responses, market prices, and investment simulations do not constitute financial advice.

Distributed under the MIT License.
</details>