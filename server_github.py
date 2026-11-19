# -*- coding: utf-8 -*-
"""World Strategy Web Game - local Python server. All combat is abstract game scoring."""
import os, sqlite3, secrets, time, re
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory, g, Response

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "world_game.db")
ADMIN_PASSWORD = os.environ.get("GAME_ADMIN_PASSWORD", "")
app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("GAME_SECRET_KEY") or "CHANGE-THIS-TO-A-LONG-RANDOM-SECRET-BEFORE-PUBLIC-USE"
# برای GitHub Pages و سرور تونل‌شده:
# GAME_ALLOWED_ORIGIN باید دقیقاً آدرس GitHub Pages باشد.
# GAME_COOKIE_SECURE=1 را فقط وقتی سرور از HTTPS عمومی در دسترس است تنظیم کن.
COOKIE_SECURE = os.environ.get("GAME_COOKIE_SECURE", "0") == "1"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None" if COOKIE_SECURE else "Lax",
    SESSION_COOKIE_SECURE=COOKIE_SECURE,
)
ALLOWED_ORIGIN = os.environ.get("GAME_ALLOWED_ORIGIN", "").rstrip("/")

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "").rstrip("/")
    if ALLOWED_ORIGIN and origin == ALLOWED_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response

COUNTRIES = ['افغانستان', 'آلبانی', 'الجزایر', 'آندورا', 'آنگولا', 'آنتیگوا و باربودا', 'آرژانتین', 'ارمنستان', 'استرالیا', 'اتریش', 'آذربایجان', 'باهاما', 'بحرین', 'بنگلادش', 'باربادوس', 'بلاروس', 'بلژیک', 'بلیز', 'بنین', 'بوتان', 'بولیوی', 'بوسنی و هرزگوین', 'بوتسوانا', 'برزیل', 'برونئی', 'بلغارستان', 'بورکینافاسو', 'بوروندی', 'کامبوج', 'کامرون', 'کانادا', 'کیپ ورد', 'جمهوری آفریقای مرکزی', 'چاد', 'شیلی', 'چین', 'کلمبیا', 'کومور', 'کنگو', 'کاستاریکا', 'ساحل عاج', 'کرواسی', 'کوبا', 'قبرس', 'چک', 'دانمارک', 'جیبوتی', 'دومینیکا', 'جمهوری دومینیکن', 'اکوادور', 'مصر', 'السالوادور', 'گینه استوایی', 'اریتره', 'استونی', 'اسواتینی', 'اتیوپی', 'فیجی', 'فنلاند', 'فرانسه', 'گابن', 'گامبیا', 'گرجستان', 'آلمان', 'غنا', 'یونان', 'گرنادا', 'گواتمالا', 'گینه', 'گینه بیسائو', 'گویان', 'هائیتی', 'هندوراس', 'مجارستان', 'ایسلند', 'هند', 'اندونزی', 'ایران', 'عراق', 'ایرلند', 'اسرائیل', 'ایتالیا', 'جامائیکا', 'ژاپن', 'اردن', 'قزاقستان', 'کنیا', 'کیریباتی', 'کره شمالی', 'کره جنوبی', 'کویت', 'قرقیزستان', 'لائوس', 'لتونی', 'لبنان', 'لسوتو', 'لیبریا', 'لیبی', 'لیختن\u200cاشتاین', 'لیتوانی', 'لوکزامبورگ', 'ماداگاسکار', 'مالاوی', 'مالزی', 'مالدیو', 'مالی', 'مالت', 'جزایر مارشال', 'موریتانی', 'موریس', 'مکزیک', 'میکرونزی', 'مولداوی', 'موناکو', 'مغولستان', 'مونته\u200cنگرو', 'مراکش', 'موزامبیک', 'میانمار', 'نامیبیا', 'نائورو', 'نپال', 'هلند', 'نیوزیلند', 'نیکاراگوئه', 'نیجر', 'نیجریه', 'مقدونیه شمالی', 'نروژ', 'عمان', 'پاکستان', 'پالائو', 'فلسطین', 'پاناما', 'پاپوآ گینه نو', 'پاراگوئه', 'پرو', 'فیلیپین', 'لهستان', 'پرتغال', 'قطر', 'رومانی', 'روسیه', 'رواندا', 'ساموآ', 'سان مارینو', 'عربستان سعودی', 'سنگال', 'صربستان', 'سیشل', 'سیرالئون', 'سنگاپور', 'اسلواکی', 'اسلوونی', 'جزایر سلیمان', 'سومالی', 'آفریقای جنوبی', 'سودان جنوبی', 'اسپانیا', 'سریلانکا', 'سودان', 'سورینام', 'سوئد', 'سوئیس', 'سوریه', 'تاجیکستان', 'تانزانیا', 'تایلند', 'تیمور شرقی', 'توگو', 'تونس', 'ترکیه', 'ترکمنستان', 'تووالو', 'اوگاندا', 'اوکراین', 'امارات متحده عربی', 'بریتانیا', 'ایالات متحده آمریکا', 'اروگوئه', 'ازبکستان', 'وانواتو', 'واتیکان', 'ونزوئلا', 'ویتنام', 'یمن', 'زامبیا', 'زیمبابوه', 'جمهوری دموکراتیک کنگو']
SHOP = {'oil_big': ('چاه نفت بزرگ', 600000, 'income', 10, 5), 'oil_small': ('چاه نفت کوچک', 400000, 'income', 5, 5), 'diamond': ('معدن الماس', 100000, 'income', 280000, 5), 'gold': ('معدن طلا', 50000, 'income', 150000, 5), 'ruby': ('معدن یاقوت', 50000, 'income', 150000, 5), 'silver': ('معدن نقره', 40000, 'income', 80000, 5), 'iron': ('معدن آهن', 30000, 'income', 900000, 5), 'B2': ('بمب\u200cافکن B2', 2000000, 'aircraft', 0, 100), 'F35': ('جنگنده F35', 700000, 'aircraft', 0, 100), 'F15': ('جنگنده F15', 580000, 'aircraft', 0, 100), 'F5': ('جنگنده F5', 400000, 'aircraft', 0, 100), 'MQ9': ('پهپاد MQ9', 600000, 'aircraft', 0, 100), 'MQ4': ('پهپاد MQ4', 400000, 'aircraft', 0, 100), 'Arash2': ('پهپاد انتحاری آرش ۲', 200000, 'weapon', 2, 100), 'Arash1': ('پهپاد انتحاری آرش ۱', 100000, 'weapon', 1, 100), 'Shahed136': ('پهپاد شاهد ۱۳۶', 200000, 'weapon', 2, 100), 'N2': ('بمب N2', 600000, 'weapon', 10, 100), 'M60': ('موشک M60', 400000, 'weapon', 5, 100), 'Lamsab': ('موشک لامصب', 300000, 'weapon', 3, 100), 'DroneMissile': ('موشک پهپاد', 200000, 'weapon', 2, 100), 'Sejjil': ('موشک سجیل', 2500000, 'weapon', 20, 5), 'Tomahawk': ('موشک تاماهاوک', 1000000, 'weapon', 10, 5), 'Khyber': ('موشک خیبرشکن', 500000, 'weapon', 3, 5), 'SpecialB2': ('موشک ویژه ضد پدافند بمب\u200cافکن', 700000, 'weapon', 2, 100), 'SpecialFighter': ('موشک ویژه ضد پدافند جنگنده', 350000, 'weapon', 1, 100), 'NukeSuper': ('بمب اتم فوق سنگین (فقط بازی)', 2500000, 'nuclear', 20, 100), 'NukeHeavy': ('بمب اتم سنگین (فقط بازی)', 1700000, 'nuclear', 15, 100), 'NukeLight': ('بمب اتم سبک (فقط بازی)', 800000, 'nuclear', 5, 100), 'B2Defense': ('پدافند بمب\u200cافکن B2', 750000, 'defense', 0, 100), 'FighterDefense': ('پدافند جنگنده', 400000, 'defense', 0, 100), 'AdvancedDroneDefense': ('پدافند پهپاد پیشرفته', 300000, 'defense', 0, 100), 'DroneDefense': ('پدافند پهپاد معمولی', 200000, 'defense', 0, 100), 'NuclearDefense': ('موشک ضد اتم', 550000, 'defense', 0, 100), 'AssetHacker': ('هکر دارایی (رویداد داخل بازی)', 500000, 'special', 0, 100), 'DefenseHacker': ('هکر پدافند (رویداد داخل بازی)', 200000, 'special', 0, 100), 'AntiHacker': ('ضد هکر', 200000, 'special', 0, 100), 'Spy': ('جاسوس دارایی (داخل بازی)', 250000, 'special', 0, 100), 'AntiSpy': ('ضد جاسوس', 300000, 'special', 0, 100), 'Virus': ('عملیات ویروسی خیالی', 500000, 'special', 0, 100)}
SPECIAL = {"ایالات متحده آمریکا","بریتانیا","کره شمالی","هند","پاکستان","فرانسه","چین","اسرائیل","روسیه"}

def conn():
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with conn() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS players(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
          password TEXT NOT NULL, display_name TEXT NOT NULL, country TEXT UNIQUE,
          money INTEGER NOT NULL DEFAULT 1000000, oil INTEGER NOT NULL DEFAULT 0,
          health INTEGER NOT NULL DEFAULT 100, banned INTEGER NOT NULL DEFAULT 0,
          attacks INTEGER NOT NULL DEFAULT 0, defenses INTEGER NOT NULL DEFAULT 0,
          captured INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS inventory(
          player_id INTEGER NOT NULL, item TEXT NOT NULL, qty INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(player_id,item), FOREIGN KEY(player_id) REFERENCES players(id));
        CREATE TABLE IF NOT EXISTS alliances(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, owner INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS alliance_members(
          alliance_id INTEGER NOT NULL, player_id INTEGER UNIQUE NOT NULL,
          PRIMARY KEY(alliance_id,player_id));
        CREATE TABLE IF NOT EXISTS oil_orders(
          id INTEGER PRIMARY KEY AUTOINCREMENT, seller INTEGER NOT NULL, qty INTEGER NOT NULL,
          price INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS game_settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT OR IGNORE INTO game_settings(key,value) VALUES('active','1');
        """)
def current():
    if "pid" not in session: return None
    with conn() as db:
        return db.execute("SELECT * FROM players WHERE id=?", (session["pid"],)).fetchone()
def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        p=current()
        if not p: return jsonify(error="ابتدا وارد حساب شو."), 401
        if p["banned"]: return jsonify(error="حساب مسدود است."), 403
        return fn(*a, **kw)
    return wrapper
def game_active():
    with conn() as db:
        return db.execute("SELECT value FROM game_settings WHERE key='active'").fetchone()["value"] == "1"
def err(msg, code=400): return jsonify(error=msg), code

# The HTML is embedded as a fallback because Pydroid may execute server.py from a temporary folder.
INDEX_HTML = '<!doctype html>\n<html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>بازی استراتژی جهان</title><style>\n*{box-sizing:border-box}body{margin:0;background:#0b1220;color:#e8eef8;font-family:Tahoma,Arial,sans-serif}header{padding:18px;background:#111c30;border-bottom:1px solid #26364f;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}h1{font-size:20px;margin:0}.muted{color:#9fb0c8;font-size:12px}.wrap{max-width:1100px;margin:auto;padding:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.card{background:#121e32;border:1px solid #26364f;border-radius:14px;padding:15px}.card h2{font-size:16px;margin:0 0 12px}.row{display:flex;gap:8px;flex-wrap:wrap}input,select,button{font:inherit;border-radius:9px;border:1px solid #344965;padding:10px;background:#0b1628;color:#eef5ff;min-width:0}input,select{width:100%;margin:5px 0}button{background:#2456a6;border:0;cursor:pointer;margin:4px 0}button.secondary{background:#29384e}button.danger{background:#963d4b}.hidden{display:none}.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.stat{background:#0c1729;padding:10px;border-radius:10px}.stat b{display:block;font-size:17px;margin-top:5px}.list{max-height:220px;overflow:auto;font-size:13px}.item{padding:8px;border-bottom:1px solid #26364f;display:flex;justify-content:space-between;gap:8px}.notice{padding:10px;background:#172b48;border-radius:10px;margin:10px 0}.good{color:#70d6a1}.bad{color:#ff9b9b}\n</style></head><body>\n<header><div><h1>🌍 بازی استراتژی جهان</h1><div class="muted">دنیای مشترک چندنفره • نسخه آزمایشی وب</div></div><div id="status" class="muted">در حال اتصال...</div></header>\n<div class="wrap">\n<div id="auth" class="grid">\n<section class="card"><h2>ساخت حساب جدید</h2><input id="rname" placeholder="نام نمایشی"><input id="ruser" placeholder="نام کاربری (۳ تا ۲۰ حرف/عدد)"><input id="rpass" type="password" placeholder="رمز عبور (حداقل ۸ نویسه)"><button onclick="register()">ثبت\u200cنام و ورود</button></section>\n<section class="card"><h2>ورود بازیکن</h2><input id="luser" placeholder="نام کاربری"><input id="lpass" type="password" placeholder="رمز عبور"><button onclick="login()">ورود</button><div id="authmsg" class="muted"></div></section>\n</div>\n<div id="game" class="hidden">\n<div class="notice" id="hello"></div>\n<div class="grid">\n<section class="card"><h2>👤 کشور و پروفایل</h2><div id="stats" class="stats"></div><div id="countrybox"></div><button class="secondary" onclick="refresh()">به\u200cروزرسانی</button><button class="secondary" onclick="logout()">خروج</button></section>\n<section class="card"><h2>🛒 فروشگاه بازی</h2><select id="shopitem"></select><button onclick="buy()">خرید آیتم</button><div id="inventory" class="list"></div></section>\n<section class="card"><h2>⚔️ نبرد امتیازی و تصرف کشور</h2><select id="target"></select><button onclick="attack()">ثبت نبرد</button><div class="muted">نتیجه بر اساس امتیازهای داخل بازی محاسبه می\u200cشود.</div></section>\n<section class="card"><h2>💸 انتقال پول</h2><select id="transferTarget"></select><input id="transferAmount" type="number" min="1" placeholder="مبلغ"><button onclick="transfer()">انتقال</button></section>\n<section class="card"><h2>🤝 اتحادها</h2><input id="allianceName" placeholder="نام اتحاد جدید"><button onclick="alliance(\'create\')">ساخت اتحاد</button><select id="allianceSelect"></select><div class="row"><button onclick="alliance(\'join\')">عضویت</button><button class="secondary" onclick="alliance(\'leave\')">خروج از اتحاد</button></div><div id="myall" class="muted"></div></section>\n<section class="card"><h2>🛢️ بازار نفت</h2><input id="oilqty" type="number" placeholder="تعداد بشکه برای فروش"><input id="oilprice" type="number" placeholder="قیمت هر بشکه"><button onclick="sellOil()">ثبت سفارش فروش</button><div id="orders" class="list"></div></section>\n<section class="card"><h2>🔐 مدیریت بازی</h2><input id="adminpass" type="password" placeholder="رمز مدیر"><button onclick="adminLogin()">ورود مدیر</button><div id="adminarea" class="hidden"><button onclick="toggleGame(false)" class="danger">غیرفعال کردن بازی</button><button onclick="toggleGame(true)">فعال کردن بازی</button><button class="secondary" onclick="adminPlayers()">فهرست بازیکنان</button><div id="adminplayers" class="list"></div></div></section>\n</div></div><div id="toast" class="notice hidden"></div></div>\n<script>\nlet S=null;const $=id=>document.getElementById(id);\nasync function api(url,data){let r=await fetch(\'/api/\'+url,{method:data?\'POST\':\'GET\',headers:data?{\'Content-Type\':\'application/json\'}:{},body:data?JSON.stringify(data):undefined});let j=await r.json();if(!r.ok)throw Error(j.error||\'خطا\');return j}\nfunction msg(t){$(\'toast\').textContent=t;$(\'toast\').classList.remove(\'hidden\');setTimeout(()=>$(\'toast\').classList.add(\'hidden\'),4500)}\nasync function status(){try{let s=await api(\'status\');$(\'status\').textContent=(s.active?\'🟢 بازی فعال\':\'🔴 بازی غیرفعال\')+\' • \'+s.players+\' بازیکن\'}catch(e){$(\'status\').textContent=\'اتصال برقرار نشد\'}}\nasync function register(){try{await api(\'register\',{name:$(\'rname\').value,username:$(\'ruser\').value,password:$(\'rpass\').value});await refresh()}catch(e){$(\'authmsg\').textContent=e.message}}\nasync function login(){try{await api(\'login\',{username:$(\'luser\').value,password:$(\'lpass\').value});await refresh()}catch(e){$(\'authmsg\').textContent=e.message}}\nasync function logout(){await api(\'logout\',{});S=null;$(\'game\').classList.add(\'hidden\');$(\'auth\').classList.remove(\'hidden\');status()}\nasync function refresh(){try{S=await api(\'state\');$(\'auth\').classList.add(\'hidden\');$(\'game\').classList.remove(\'hidden\');render()}catch(e){$(\'auth\').classList.remove(\'hidden\');$(\'game\').classList.add(\'hidden\');$(\'authmsg\').textContent=e.message}}\nfunction opt(arr,label){return arr.map(x=>`<option value="${x.id}">${label(x)}</option>`).join(\'\')}\nfunction render(){let p=S.player;$(\'hello\').textContent=\'خوش آمدی \'+p.display_name+\'؛ \'+(p.country||\'هنوز کشوری انتخاب نکرده\u200cای\');$(\'stats\').innerHTML=[[\'کشور\',p.country||\'ندارد\'],[\'پول\',p.money.toLocaleString()+\' $\'],[\'نفت\',p.oil.toLocaleString()],[\'سلامتی\',p.health+\'٪\'],[\'حملات\',p.attacks],[\'تصرف\u200cها\',p.captured]].map(x=>`<div class="stat">${x[0]}<b>${x[1]}</b></div>`).join(\'\');\n$(\'countrybox\').innerHTML=p.country?\'کشور ثبت شده: \'+p.country:`<select id="country"><option value="">انتخاب کشور آزاد</option>${S.countries.map(c=>`<option>${c}</option>`).join(\'\')}</select><button onclick="chooseCountry()">انتخاب کشور</button>`;\n$(\'shopitem\').innerHTML=Object.entries(S.shop).map(([k,v])=>`<option value="${k}">${v.name} — ${v.price.toLocaleString()}$</option>`).join(\'\');\n$(\'inventory\').innerHTML=\'<b>موجودی:</b>\'+ (S.inventory.map(x=>`<div class="item">${S.shop[x.item]?.name||x.item}<b>${x.qty}</b></div>`).join(\'\')||\'<div class="muted">خالی</div>\');\nlet targets=S.players.filter(x=>x.country);$(\'target\').innerHTML=opt(targets,x=>`${x.display_name} — ${x.country}`);$(\'transferTarget\').innerHTML=opt(S.players,x=>x.display_name+\' (#\'+x.id+\')\');\n$(\'allianceSelect\').innerHTML=opt(S.alliances,x=>x.name+\' (\'+x.members+\' عضو)\');$(\'myall\').textContent=S.my_alliance?\'عضو اتحاد: \'+S.my_alliance.name:\'عضو اتحادی نیستی\';\n$(\'orders\').innerHTML=S.orders.map(x=>`<div class="item">#${x.id} • ${x.seller} • ${x.qty} بشکه • هرکدام ${x.price.toLocaleString()}$ <button onclick="buyOil(${x.id})">خرید</button></div>`).join(\'\')||\'سفارشی نیست\';\n}\nasync function chooseCountry(){try{await api(\'country\',{country:$(\'country\').value});await refresh()}catch(e){msg(e.message)}}\nasync function buy(){try{await api(\'buy\',{item:$(\'shopitem\').value});msg(\'خرید انجام شد\');await refresh()}catch(e){msg(e.message)}}\nasync function attack(){try{let r=await api(\'attack\',{target:$(\'target\').value});msg(r.message);await refresh()}catch(e){msg(e.message)}}\nasync function transfer(){try{await api(\'transfer\',{target:$(\'transferTarget\').value,amount:+$(\'transferAmount\').value});msg(\'انتقال انجام شد\');await refresh()}catch(e){msg(e.message)}}\nasync function alliance(action){try{let d={action};if(action===\'create\')d.name=$(\'allianceName\').value;if(action===\'join\')d.id=$(\'allianceSelect\').value;await api(\'alliance\',d);msg(\'درخواست انجام شد\');await refresh()}catch(e){msg(e.message)}}\nasync function sellOil(){try{await api(\'oil/sell\',{qty:+$(\'oilqty\').value,price:+$(\'oilprice\').value});msg(\'سفارش ثبت شد\');await refresh()}catch(e){msg(e.message)}}\nasync function buyOil(id){try{await api(\'oil/buy\',{id});msg(\'خرید نفت انجام شد\');await refresh()}catch(e){msg(e.message)}}\nasync function adminLogin(){try{await api(\'admin/login\',{password:$(\'adminpass\').value});$(\'adminarea\').classList.remove(\'hidden\');msg(\'ورود مدیر موفق بود\')}catch(e){msg(e.message)}}\nasync function toggleGame(active){try{await api(\'admin/toggle\',{active});msg(active?\'بازی فعال شد\':\'بازی غیرفعال شد\');status()}catch(e){msg(e.message)}}\nasync function adminPlayers(){try{let r=await api(\'admin/players\');$(\'adminplayers\').innerHTML=r.players.map(p=>`<div class="item">#${p.id} ${p.display_name} • ${p.country||\'بدون کشور\'} <button class="danger" onclick="ban(${p.id},${!p.banned})">${p.banned?\'رفع مسدودی\':\'مسدود\'}</button></div>`).join(\'\')}catch(e){msg(e.message)}}\nasync function ban(id,banned){try{await api(\'admin/ban\',{id,banned});adminPlayers()}catch(e){msg(e.message)}}\nstatus();refresh();setInterval(status,10000);setInterval(()=>{if(S)refresh()},15000);\n</script></body></html>'

@app.get("/")
def home():
    page = os.path.join(BASE, "index.html")
    if os.path.isfile(page):
        return send_from_directory(BASE, "index.html")
    return Response(INDEX_HTML, mimetype="text/html; charset=utf-8")
@app.get("/api/status")
def status():
    with conn() as db:
        n=db.execute("SELECT COUNT(*) n FROM players").fetchone()["n"]
    return jsonify(active=game_active(), players=n, logged=bool(current()))
@app.post("/api/register")
def register():
    d=request.get_json(force=True); u=str(d.get("username","")).strip().lower()
    pw=str(d.get("password","")); name=str(d.get("name","")).strip()[:32]
    if not game_active(): return err("بازی فعلاً توسط مدیر غیرفعال شده است.", 503)
    if not re_username(u) or len(pw)<8 or not name: return err("نام کاربری ۳ تا ۲۰ حرف/عدد و رمز حداقل ۸ نویسه باشد.")
    from werkzeug.security import generate_password_hash
    with conn() as db:
        try:
            cur=db.execute("INSERT INTO players(username,password,display_name,created) VALUES(?,?,?,?)",
                           (u, generate_password_hash(pw), name, int(time.time())))
            pid=cur.lastrowid
        except sqlite3.IntegrityError: return err("این نام کاربری قبلاً ثبت شده است.")
    session["pid"]=pid
    return jsonify(ok=True)
def re_username(s):
    return 3<=len(s)<=20 and s.replace("_","").isalnum()
@app.post("/api/login")
def login():
    from werkzeug.security import check_password_hash
    d=request.get_json(force=True); u=str(d.get("username","")).strip().lower(); pw=str(d.get("password",""))
    with conn() as db: p=db.execute("SELECT * FROM players WHERE username=?", (u,)).fetchone()
    if not p or not check_password_hash(p["password"],pw): return err("نام کاربری یا رمز اشتباه است.",401)
    if p["banned"]: return err("حساب مسدود است.",403)
    session["pid"]=p["id"]; return jsonify(ok=True)
@app.post("/api/logout")
def logout(): session.clear(); return jsonify(ok=True)
@app.get("/api/state")
@login_required
def state():
    p=current()
    with conn() as db:
        inv=db.execute("SELECT item,qty FROM inventory WHERE player_id=? AND qty>0",(p["id"],)).fetchall()
        players=db.execute("SELECT id,display_name,country,health FROM players WHERE banned=0 ORDER BY display_name").fetchall()
        orders=db.execute("SELECT o.id,o.qty,o.price,p.display_name seller FROM oil_orders o JOIN players p ON p.id=o.seller WHERE o.active=1").fetchall()
        als=db.execute("SELECT a.id,a.name,a.owner,COUNT(m.player_id) members FROM alliances a LEFT JOIN alliance_members m ON m.alliance_id=a.id GROUP BY a.id").fetchall()
        occupied={r["country"] for r in db.execute("SELECT country FROM players WHERE country IS NOT NULL")}
        myall=db.execute("SELECT a.id,a.name FROM alliances a JOIN alliance_members m ON m.alliance_id=a.id WHERE m.player_id=?",(p["id"],)).fetchone()
    return jsonify(player={k:p[k] for k in ("id","username","display_name","country","money","oil","health","attacks","defenses","captured")},
      inventory=[dict(x) for x in inv], players=[dict(x) for x in players if x["id"]!=p["id"]],
      countries=[c for c in COUNTRIES if c not in occupied and c not in SPECIAL],
      orders=[dict(x) for x in orders], alliances=[dict(x) for x in als], my_alliance=dict(myall) if myall else None,
      shop={k:{"name":v[0],"price":v[1],"category":v[2]} for k,v in SHOP.items()})
@app.post("/api/country")
@login_required
def country():
    d=request.get_json(force=True); c=str(d.get("country",""))
    if c not in COUNTRIES or c in SPECIAL: return err("این کشور برای انتخاب عادی در دسترس نیست.")
    p=current()
    if p["country"]: return err("قبلاً کشور انتخاب کرده‌ای.")
    with conn() as db:
        try: db.execute("UPDATE players SET country=? WHERE id=?",(c,p["id"]))
        except sqlite3.IntegrityError: return err("این کشور قبلاً انتخاب شده است.")
    return jsonify(ok=True)
@app.post("/api/buy")
@login_required
def buy():
    d=request.get_json(force=True); key=str(d.get("item",""))
    if key not in SHOP: return err("کالای نامعتبر.")
    p=current(); name,price,cat,val,limit=SHOP[key]
    if not p["country"]: return err("اول کشور انتخاب کن.")
    with conn() as db:
        row=db.execute("SELECT qty FROM inventory WHERE player_id=? AND item=?",(p["id"],key)).fetchone()
        qty=row["qty"] if row else 0
        if qty>=limit: return err("سقف مالکیت پر شده.")
        if p["money"]<price: return err("پول کافی نیست.")
        db.execute("UPDATE players SET money=money-? WHERE id=?",(price,p["id"]))
        db.execute("INSERT INTO inventory VALUES(?,?,1) ON CONFLICT(player_id,item) DO UPDATE SET qty=qty+1",(p["id"],key))
    return jsonify(ok=True)
@app.post("/api/attack")
@login_required
def attack():
    # Abstract, turn-based game points only; no real-world weapon guidance.
    d=request.get_json(force=True); target=int(d.get("target",0)); p=current()
    with conn() as db:
        a=db.execute("SELECT * FROM players WHERE id=?",(p["id"],)).fetchone()
        t=db.execute("SELECT * FROM players WHERE id=? AND banned=0",(target,)).fetchone()
        if not t or target==p["id"]: return err("بازیکن هدف معتبر نیست.")
        if not a["country"] or not t["country"]: return err("هر دو بازیکن باید کشور داشته باشند.")
        if a["health"]<1 or t["health"]<1: return err("سلامتی کافی نیست.")
        # A simple random-free points contest: stronger current health wins a fixed game round.
        if a["health"] < t["health"]: return err("این دور را نبردی؛ ابتدا امتیاز دفاعی/سلامتی بازی را افزایش بده.")
        old=t["country"]
        db.execute("UPDATE players SET health=MAX(0,health-25),attacks=attacks+1 WHERE id=?",(target,))
        db.execute("UPDATE players SET health=MAX(0,health-10),attacks=attacks+1 WHERE id=?",(p["id"],))
        t2=db.execute("SELECT health FROM players WHERE id=?",(target,)).fetchone()
        if t2["health"]==0:
            db.execute("UPDATE players SET country=NULL,health=100 WHERE id=?",(target,))
            db.execute("UPDATE players SET country=?,captured=captured+1 WHERE id=?",(old,p["id"]))
            return jsonify(ok=True,message="در نبرد امتیازی پیروز شدی و کشور هدف را تصرف کردی.")
    return jsonify(ok=True,message="دور بازی ثبت شد؛ امتیاز سلامتی هر دو کشور به‌روزرسانی شد.")
@app.post("/api/transfer")
@login_required
def transfer():
    d=request.get_json(force=True); target=int(d.get("target",0)); amount=int(d.get("amount",0)); p=current()
    if amount<=0 or target==p["id"]: return err("مقدار یا مقصد نامعتبر است.")
    with conn() as db:
        a=db.execute("SELECT money FROM players WHERE id=?",(p["id"],)).fetchone()
        b=db.execute("SELECT id FROM players WHERE id=? AND banned=0",(target,)).fetchone()
        if not b or a["money"]<amount: return err("بازیکن پیدا نشد یا پول کافی نیست.")
        db.execute("UPDATE players SET money=money-? WHERE id=?",(amount,p["id"]))
        db.execute("UPDATE players SET money=money+? WHERE id=?",(amount,target))
    return jsonify(ok=True)
@app.post("/api/alliance")
@login_required
def alliance():
    d=request.get_json(force=True); action=d.get("action"); p=current()
    with conn() as db:
        membership=db.execute("SELECT alliance_id FROM alliance_members WHERE player_id=?",(p["id"],)).fetchone()
        if action=="create":
            name=str(d.get("name","")).strip()
            if not 3<=len(name)<=30: return err("نام اتحاد باید ۳ تا ۳۰ نویسه باشد.")
            if membership: return err("ابتدا از اتحاد فعلی خارج شو.")
            try:
                cur=db.execute("INSERT INTO alliances(name,owner) VALUES(?,?)",(name,p["id"]))
                db.execute("INSERT INTO alliance_members VALUES(?,?)",(cur.lastrowid,p["id"]))
            except sqlite3.IntegrityError: return err("نام اتحاد تکراری است.")
        elif action=="join":
            aid=int(d.get("id",0))
            if membership: return err("ابتدا از اتحاد فعلی خارج شو.")
            if not db.execute("SELECT 1 FROM alliances WHERE id=?",(aid,)).fetchone(): return err("اتحاد پیدا نشد.")
            db.execute("INSERT INTO alliance_members VALUES(?,?)",(aid,p["id"]))
        elif action=="leave":
            if not membership: return err("عضو اتحادی نیستی.")
            aid=membership["alliance_id"]
            owner=db.execute("SELECT owner FROM alliances WHERE id=?",(aid,)).fetchone()["owner"]
            if owner==p["id"]:
                nxt=db.execute("SELECT player_id FROM alliance_members WHERE alliance_id=? AND player_id<>? ORDER BY player_id LIMIT 1",(aid,p["id"])).fetchone()
                if nxt: db.execute("UPDATE alliances SET owner=? WHERE id=?",(nxt["player_id"],aid))
                else: db.execute("DELETE FROM alliances WHERE id=?",(aid,))
            db.execute("DELETE FROM alliance_members WHERE player_id=?",(p["id"],))
        else: return err("عملیات ناشناخته.")
    return jsonify(ok=True)
@app.post("/api/oil/sell")
@login_required
def oil_sell():
    d=request.get_json(force=True); qty=int(d.get("qty",0)); price=int(d.get("price",0)); p=current()
    if qty<=0 or price<=0 or p["oil"]<qty: return err("مقدار یا موجودی نفت نامعتبر است.")
    with conn() as db:
        db.execute("UPDATE players SET oil=oil-? WHERE id=?",(qty,p["id"]))
        db.execute("INSERT INTO oil_orders(seller,qty,price) VALUES(?,?,?)",(p["id"],qty,price))
    return jsonify(ok=True)
@app.post("/api/oil/buy")
@login_required
def oil_buy():
    d=request.get_json(force=True); oid=int(d.get("id",0)); p=current()
    with conn() as db:
        o=db.execute("SELECT * FROM oil_orders WHERE id=? AND active=1",(oid,)).fetchone()
        if not o or o["seller"]==p["id"]: return err("سفارش معتبر نیست.")
        total=o["qty"]*o["price"]
        if p["money"]<total: return err("پول کافی نیست.")
        db.execute("UPDATE players SET money=money-?,oil=oil+? WHERE id=?",(total,o["qty"],p["id"]))
        db.execute("UPDATE players SET money=money+? WHERE id=?",(total,o["seller"]))
        db.execute("UPDATE oil_orders SET active=0 WHERE id=?",(oid,))
    return jsonify(ok=True)
@app.post("/api/admin/login")
def admin_login():
    d=request.get_json(force=True)
    if not ADMIN_PASSWORD: return err("رمز مدیر در متغیر محیطی GAME_ADMIN_PASSWORD تنظیم نشده است.",503)
    if not secrets.compare_digest(str(d.get("password","")),ADMIN_PASSWORD): return err("رمز مدیر اشتباه است.",401)
    session["admin"]=True; return jsonify(ok=True)
@app.post("/api/admin/toggle")
def admin_toggle():
    if not session.get("admin"): return err("دسترسی مدیر لازم است.",403)
    d=request.get_json(force=True); value="1" if d.get("active") else "0"
    with conn() as db: db.execute("UPDATE game_settings SET value=? WHERE key='active'",(value,))
    return jsonify(ok=True,active=value=="1")
@app.get("/api/admin/players")
def admin_players():
    if not session.get("admin"): return err("دسترسی مدیر لازم است.",403)
    with conn() as db:
        rows=db.execute("SELECT id,username,display_name,country,money,health,banned FROM players ORDER BY id DESC").fetchall()
    return jsonify(players=[dict(x) for x in rows])
@app.post("/api/admin/ban")
def admin_ban():
    if not session.get("admin"): return err("دسترسی مدیر لازم است.",403)
    d=request.get_json(force=True)
    with conn() as db: db.execute("UPDATE players SET banned=? WHERE id=?",(1 if d.get("banned") else 0,int(d.get("id",0))))
    return jsonify(ok=True)

if __name__ == "__main__":
    init_db()
    print("World Game is running: http://127.0.0.1:8000")
    print("For internet access, expose port 8000 through a trusted secure tunnel.")
    app.run(host="0.0.0.0", port=8000, debug=False)
