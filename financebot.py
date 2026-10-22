import os
import asyncio
import logging
import sqlite3
import discord
from discord.ext import commands
import pandas as pd
from pydantic import BaseModel, Field
import yfinance as yf
from dotenv import load_dotenv
from google import genai
from google.genai import types
load_dotenv()

logging.getLogger("google_genai.models").setLevel(logging.ERROR)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

client = genai.Client(api_key=GOOGLE_API_KEY)

# Lista de fallback ajustada según tus modelos de texto disponibles

MODELOS_FALLBACK = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3-flash",
    "gemini-3.8-flash",
]

# ==========================================
# 1. BASE DE DATOS Y TABLAS (SQLite)
# ==========================================
conn = sqlite3.connect("smart_wallet.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movimientos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo        TEXT NOT NULL,
    categoria   TEXT NOT NULL,
    monto       REAL NOT NULL,
    descripcion TEXT NOT NULL,
    fecha       TEXT DEFAULT (datetime('now', '-5 hours'))
)
""")
conn.commit()


def ver_tabla():
    return pd.read_sql_query("SELECT * FROM movimientos ORDER BY id", conn)


# ==========================================
# 2. HERRAMIENTAS / TOOLS (Function Calling)
# ==========================================


def consultar_saldo_cuenta(cuenta: str) -> dict:
    """Consulta el saldo de una cuenta específica de la billetera demo.

    Args:
        cuenta: Nombre de la cuenta a consultar. Opciones válidas: 'efectivo', 'banco' o 'yappy'.
    """
    BILLETERA_DEMO = {"efectivo": 45.75, "banco": 2.30, "yappy": 3.10}
    cuenta = cuenta.strip().lower()
    print(f"   [TOOL] consultar_saldo_cuenta(cuenta='{cuenta}')")

    if cuenta not in BILLETERA_DEMO:
        return {
            "ok": False,
            "error": f"La cuenta '{cuenta}' no existe. Usa: efectivo, banco o yappy.",
        }

    return {"ok": True, "cuenta": cuenta, "saldo_usd": BILLETERA_DEMO[cuenta]}


def registrar_movimiento(
    tipo: str, categoria: str, monto: float, descripcion: str
) -> dict:
    """Guarda un ingreso o un gasto en la base de datos.
    Úsala SIEMPRE que el usuario diga que cobró, recibió, ganó, gastó, pagó o compró algo.

    Args:
        tipo: Exactamente 'ingreso' (entra dinero) o 'gasto' (sale dinero).
        categoria: Una de: 'comida', 'transporte', 'entretenimiento', 'educacion', 'salud', 'servicios', 'ingresos', 'otros'.
        monto: Cantidad en dólares, número positivo. Ejemplo: 12.50
        descripcion: Detalle breve. Ejemplos: 'almuerzo en la fonda', 'beca IFARHU'.
    """
    tipo = tipo.strip().lower()
    categoria = categoria.strip().lower()
    monto = round(float(monto), 2)

    if tipo not in ("ingreso", "gasto"):
        return {"ok": False, "error": "El tipo debe ser 'ingreso' o 'gasto'."}
    if monto <= 0:
        return {"ok": False, "error": "El monto debe ser mayor que cero."}

    cursor.execute(
        "INSERT INTO movimientos (tipo, categoria, monto, descripcion) VALUES (?, ?, ?, ?)",
        (tipo, categoria, monto, descripcion),
    )
    conn.commit()

    nuevo_id = cursor.lastrowid
    print(
        f"   [SQL INSERT] #{nuevo_id} {tipo} de ${monto:.2f} en '{categoria}' ({descripcion})"
    )
    return {
        "ok": True,
        "id": nuevo_id,
        "tipo": tipo,
        "categoria": categoria,
        "monto_usd": monto,
    }


def consultar_billetera() -> dict:
    """Consulta la base de datos y devuelve: ingresos totales, gastos totales, saldo disponible,
    gastos por categoría y los últimos 5 movimientos con su id.
    """
    print("   [SQL SELECT] Consultando saldo y resumen")

    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo = 'ingreso'")
    ingresos = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT SUM(monto) FROM movimientos WHERE tipo = 'gasto'")
    gastos = cursor.fetchone()[0] or 0.0

    cursor.execute(
        "SELECT categoria, SUM(monto) FROM movimientos WHERE tipo = 'gasto' "
        "GROUP BY categoria ORDER BY SUM(monto) DESC"
    )
    gastos_por_categoria = {
        categoria: round(total, 2) for categoria, total in cursor.fetchall()
    }

    cursor.execute(
        "SELECT id, tipo, categoria, monto, descripcion FROM movimientos ORDER BY id DESC LIMIT 5"
    )
    ultimos_movimientos = [
        {
            "id": fila[0],
            "tipo": fila[1],
            "categoria": fila[2],
            "monto": fila[3],
            "descripcion": fila[4],
        }
        for fila in cursor.fetchall()
    ]

    return {
        "ok": True,
        "ingresos_totales_usd": round(ingresos, 2),
        "gastos_totales_usd": round(gastos, 2),
        "saldo_disponible_usd": round(ingresos - gastos, 2),
        "gastos_por_categoria": gastos_por_categoria,
        "ultimos_movimientos": ultimos_movimientos,
    }


def eliminar_movimiento(id_movimiento: int) -> dict:
    """Elimina un movimiento de la base de datos usando su id numérico.

    Args:
        id_movimiento: Número de id del movimiento que se desea borrar.
    """
    print(f"   [SQL DELETE] Borrando el movimiento #{id_movimiento}")

    cursor.execute(
        "DELETE FROM movimientos WHERE id = ?", (int(id_movimiento),)
    )
    conn.commit()

    if cursor.rowcount == 0:
        return {
            "ok": False,
            "error": f"No existe ningún movimiento con el id {id_movimiento}.",
        }
    return {"ok": True, "id_eliminado": id_movimiento}


def obtener_precio_activo(ticker: str) -> dict:
    """Consulta el precio más reciente, en dólares, de una acción, un ETF o una criptomoneda.

    Args:
        ticker: Símbolo de Yahoo Finance. Ejemplos: 'AAPL', 'NVDA', 'MSFT', 'SPY', 'BTC-USD', 'ETH-USD'.
    """
    ALIAS_TICKERS = {
        "BITCOIN": "BTC-USD",
        "BTC": "BTC-USD",
        "ETHEREUM": "ETH-USD",
        "ETH": "ETH-USD",
        "NVIDIA": "NVDA",
        "APPLE": "AAPL",
        "MICROSOFT": "MSFT",
    }
    PRECIOS_RESPALDO = {
        "AAPL": 341.92,
        "NVDA": 218.52,
        "MSFT": 533.40,
        "SPY": 768.22,
        "BTC-USD": 81918.85,
        "ETH-USD": 2398.08,
    }

    simbolo = ticker.strip().upper()
    simbolo = ALIAS_TICKERS.get(simbolo, simbolo)
    print(f"   [YFINANCE] Consultando el precio de {simbolo}")

    try:
        historial = yf.Ticker(simbolo).history(period="5d")
        if historial.empty:
            raise ValueError("Sin datos")
        precio = round(float(historial["Close"].iloc[-1]), 2)
        fecha = historial.index[-1].strftime("%Y-%m-%d")
        return {
            "ok": True,
            "ticker": simbolo,
            "precio_usd": precio,
            "fecha_del_dato": fecha,
            "fuente": "Yahoo Finance",
        }
    except Exception:
        if simbolo in PRECIOS_RESPALDO:
            return {
                "ok": True,
                "ticker": simbolo,
                "precio_usd": PRECIOS_RESPALDO[simbolo],
                "fuente": "RESPALDO OFFLINE",
            }
        return {
            "ok": False,
            "error": f"No se pudo obtener el precio de {simbolo}.",
        }


def simular_inversion(
    monto_inicial: float,
    aporte_mensual: float,
    tasa_anual_pct: float,
    anios: int,
) -> dict:
    """Calcula cuánto crecerá un ahorro o una inversión con interés compuesto mensual
    y aportes al final de cada mes.

    Args:
        monto_inicial: Capital inicial en dólares.
        aporte_mensual: Dinero que se agrega cada mes, en dólares (puede ser 0).
        tasa_anual_pct: Rendimiento anual esperado, en porcentaje. Ejemplo: 8.0 significa 8 %.
        anios: Cantidad de años de la inversión.
    """
    print(f"   [SIMULADOR] {anios} años al {tasa_anual_pct}% anual")

    i = (tasa_anual_pct / 100) / 12
    n = anios * 12

    if i == 0:
        valor_final = monto_inicial + aporte_mensual * n
    else:
        valor_final = monto_inicial * (1 + i) ** n + aporte_mensual * (
            (1 + i) ** n - 1
        ) / i

    total_aportado = monto_inicial + aporte_mensual * n

    return {
        "ok": True,
        "valor_final_usd": round(valor_final, 2),
        "total_aportado_usd": round(total_aportado, 2),
        "ganancia_intereses_usd": round(valor_final - total_aportado, 2),
    }


def calcular_itbms_panama(subtotal: float, porcentaje: int) -> dict:
    """Calcula el impuesto ITBMS en Panamá y el monto total a pagar.

    Args:
        subtotal: Monto base de la compra en dólares.
        porcentaje: Tasa a aplicar (7 para compras generales y 10 para licores u hospedaje).
    """
    print(f"   [ITBMS] Calculando el {porcentaje}% sobre ${subtotal}")

    impuesto = round((subtotal * porcentaje) / 100, 2)
    total = round(subtotal + impuesto, 2)

    return {
        "ok": True,
        "subtotal_usd": subtotal,
        "porcentaje": porcentaje,
        "itbms_usd": impuesto,
        "total_usd": total,
    }


TODAS_LAS_HERRAMIENTAS = [
    consultar_saldo_cuenta,
    registrar_movimiento,
    consultar_billetera,
    eliminar_movimiento,
    obtener_precio_activo,
    simular_inversion,
    calcular_itbms_panama,
]

# ==========================================
# 3. CONFIGURACIÓN DEL AGENTE DE GEMINI CON FALLBACK
# ==========================================
INSTRUCCIONES_AGENTE = """
Eres Smart Wallet, un agente experto en finanzas personales para estudiantes universitarios en Panamá.
Reglas:
1. Usa SIEMPRE tus herramientas para registrar movimientos, consultar saldos o calcular impuestos/inversiones.
2. Si tienes una herramienta para un cálculo (simular_inversion o calcular_itbms_panama), úsala en lugar de calcular de memoria.
3. Nunca inventes datos ni saldos.
4. Antes de borrar un movimiento, confirma con el usuario cuál es.
5. Responde en español, en texto plano sin usar asteriscos ni tablas, de forma breve y concisa.
6. Lo que digas sobre inversiones es información educativa, no asesoría financiera.
"""

modelos_canal = {}
sesiones_canales = {}


def crear_chat_canal(channel_id: int, modelo: str):
    return client.chats.create(
        model=modelo,
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCCIONES_AGENTE,
            tools=TODAS_LAS_HERRAMIENTAS,
        ),
    )


async def enviar_mensaje_con_fallback(ctx, mensaje_texto: str):
    """Prueba los modelos en orden. Si detecta agotamiento de tokens, cuota, sobrecarga (503) o modelo no encontrado (404), avanza al siguiente."""
    channel_id = ctx.channel.id
    model_index = 0

    if channel_id in modelos_canal:
        try:
            model_index = MODELOS_FALLBACK.index(modelos_canal[channel_id])
        except ValueError:
            model_index = 0

    while model_index < len(MODELOS_FALLBACK):
        modelo_actual = MODELOS_FALLBACK[model_index]
        try:
            if modelos_canal.get(channel_id) != modelo_actual:
                print(
                    f"   [FALLBACK] Activando modelo en canal {channel_id}: {modelo_actual}"
                )
                modelos_canal[channel_id] = modelo_actual
                sesiones_canales[channel_id] = crear_chat_canal(
                    channel_id, modelo_actual
                )

                # CORRECCIÓN: Usar ctx.channel.send en lugar de ctx.send
                if model_index > 0:
                    await ctx.channel.send(
                        f"⚠️ *Aviso: Cambiando canal al modelo `{modelo_actual}`.*"
                    )

            chat = sesiones_canales[channel_id]
            respuesta = chat.send_message(mensaje_texto)
            return respuesta

        except Exception as error:
            error_str = str(error).lower()
            errores_retry = [
                "404",
                "429",
                "503",
                "500",
                "504",
                "not_found",
                "resource_exhausted",
                "quota",
                "unavailable",
                "high demand",
                "overloaded",
            ]

            if any(e in error_str for e in errores_retry):
                print(
                    f"   [FALLBACK TRIGGER] {modelo_actual} falló. Probando siguiente modelo..."
                )
                model_index += 1
            else:
                raise error

    raise Exception(
        "Todos los modelos de la lista de respaldo están inaccesibles o agotados."
    )

# ==========================================
# 4. BOT DE DISCORD (.py)
# ==========================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print("====================================")
    print(f"Bot conectado en Discord como: {bot.user}")
    print(f"Secuencia de Fallback: {MODELOS_FALLBACK}")
    print("====================================")


@bot.command(name="start", aliases=["ayuda"])
async def comando_start(ctx):
    bienvenida = (
        f"Hola, {ctx.author.display_name}. Soy Smart Wallet, tu agente de finanzas.\n\n"
        "Escríbeme cosas como:\n"
        "- Me depositaron 300 de la beca del IFARHU\n"
        "- Gasté 2 en el Metro y 6.50 en el almuerzo de la fonda\n"
        "- ¿Cuánto saldo me queda y en qué gasto más?\n"
        "- ¿A cuánto están Bitcoin y NVIDIA hoy?\n"
        "- ¿Cuánto pago por una compra de 45 dólares con ITBMS?\n\n"
        "Comandos disponibles: !saldo !reset !ayuda"
    )
    await ctx.send(bienvenida)


@bot.command(name="modelo")
async def comando_modelo(ctx):
    modelo_actual = modelos_canal.get(ctx.channel.id, MODELOS_FALLBACK[0])
    await ctx.send(f"🤖 Actualmente estoy utilizando el modelo: `{modelo_actual}`")

@bot.command(name="saldo")
async def comando_saldo(ctx):
    datos = consultar_billetera()
    texto = (
        f"Saldo disponible: ${datos['saldo_disponible_usd']:,.2f}\n"
        f"Ingresos totales: ${datos['ingresos_totales_usd']:,.2f}\n"
        f"Gastos totales: ${datos['gastos_totales_usd']:,.2f}"
    )
    await ctx.send(texto)


@bot.command(name="reset")
async def comando_reset(ctx):
    sesiones_canales.pop(ctx.channel.id, None)
    modelos_canal.pop(ctx.channel.id, None)
    await ctx.send(
        "Conversación reiniciada. Se ha restablecido el modelo principal por defecto."
    )


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    print(f"\n[DISCORD] {message.author.display_name}: {message.content}")

    async with message.channel.typing():
        try:
            # Reintentos automáticos pasando contexto para notificar en canal
            respuesta = await enviar_mensaje_con_fallback(
                message, message.content
            )

            texto = (
                respuesta.text
                or "No tengo una respuesta para eso. Intenta preguntarlo de otra forma."
            )

            if len(texto) > 2000:
                await message.reply(texto[:1990] + "...")
            else:
                await message.reply(texto)

        except Exception as error:
            print("[ERROR]", error)
            await message.reply(
                "Ocurrió un error al procesar tu solicitud o se agotaron todas las cuotas de modelos."
            )


# Iniciar bot
async def main():
    await bot.start(DISCORD_TOKEN)


asyncio.run(main())