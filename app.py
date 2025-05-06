import json
import sqlite3
from aiohttp import web
import aiohttp_jinja2
import jinja2
import datetime
import os
from utils import Api

app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(os.path.join(os.getcwd(), "templates")))
app['https://ck45726.tw1.ru'] = '/static'
routes = web.RouteTableDef()
api = Api()

# Database connection
def get_db_connection():
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    return conn

@routes.get('/ru/{id}')
async def pay_invoice(request: web.Request) -> web.Response:
    uuid = request.match_info.get("id", "")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM Invoices WHERE id = ?", (uuid,))
    invoice = cursor.fetchone()
    conn.close()
    
    if not invoice:
        return await error_handler(request, "Счет не найден")
    
    dobj = datetime.datetime.strptime(invoice['created_at'], '%Y-%m-%dT%H:%M:%S.%f')
    if datetime.datetime.now().timestamp() > (dobj + datetime.timedelta(minutes=30)).timestamp():
        return await error_handler(request, "Счет устарел")
    
    if invoice['status'] == 'paid':
        return aiohttp_jinja2.render_template("success.html", request, context={})
    
    try:
        param = request.rel_url.query['paid']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Invoices SET status = 'paid' WHERE id = ?", (uuid,))
        conn.commit()
        conn.close()
        return web.HTTPFound(f'/ru/{uuid}')
    except KeyError:
        minutes = 30 - int((datetime.datetime.now() - dobj).total_seconds() // 60)
        seconds = 60 - int((datetime.datetime.now() - dobj).total_seconds() % 60)
        context = {
            'id': uuid,
            'amount': invoice['amount'],
            'comment': invoice['description'],
            'minutes': minutes,
            'seconds': seconds,
            'wallet': '+79991234567',  # Placeholder; integrate real wallet from payment gateway
            'qiwi_url': f"https://qiwi.com/payment/form/99?amountInteger={invoice['amount']}&amountFraction=0&currency=643&extra[%27comment%27]={invoice['description']}&blocked[0]=sum&blocked[1]=account&blocked[2]=comment"
        }
        return aiohttp_jinja2.render_template("card.html", request, context=context)

async def error_handler(request: web.Request, title: str) -> web.Response:
    return aiohttp_jinja2.render_template("error.html", request, context={'title': title})

app.add_routes(routes)
app.add_routes([web.static('/static', os.path.join(os.getcwd(), "static"))])
web.run_app(app, port=8081)