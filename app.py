from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import json
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajna_kluc_za_studenti'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    preferences = db.Column(db.String(500), default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    height = db.Column(db.Float, default=170)
    weight = db.Column(db.Float, default=70)
    gender = db.Column(db.String(10), default='male')
    age = db.Column(db.Integer, default=20)

class MealEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meal_type = db.Column(db.String(20))
    meal_name = db.Column(db.String(100))
    calories = db.Column(db.Integer)
    price = db.Column(db.Integer)
    date = db.Column(db.Date, default=date.today)

class MealPlanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    breakfast = db.Column(db.String(100))
    lunch = db.Column(db.String(100))
    dinner = db.Column(db.String(100))
    snack = db.Column(db.String(100))  
    snack_calories = db.Column(db.Integer, default=0)  
    snack_price = db.Column(db.Integer, default=0) 
    total_price = db.Column(db.Integer)
    total_calories = db.Column(db.Integer)
    budget = db.Column(db.Integer)
    goal = db.Column(db.String(50))
    date = db.Column(db.Date, default=date.today)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()
    

def calculate_bmr(height, weight, age, gender, goal='maintain'):
    if gender == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    if goal == 'weight_loss':
        daily_calories = bmr * 1.2 - 400
        daily_calories = max(daily_calories, 1500)
    elif goal == 'muscle_gain':
        daily_calories = bmr * 1.2 + 400
    else:
        daily_calories = bmr * 1.2
    
    return round(daily_calories)


MEALS = {
    "breakfast": [
        {"name": "Јогурт + мусли", "price": 35, "calories": 350, "protein": 12},
        {"name": "Сендвич со кашкавал", "price": 30, "calories": 400, "protein": 10},
        {"name": "Овесни снегулки", "price": 25, "calories": 320, "protein": 8},
        {"name": "Кајгана (2 јајца)", "price": 25, "calories": 280, "protein": 14},
        {"name": "Парче леб + сирење", "price": 20, "calories": 250, "protein": 8},
        {"name": "Банана + јогурт", "price": 28, "calories": 300, "protein": 6},
        {"name": "Протеински шејк", "price": 40, "calories": 500, "protein": 30},
        {"name": "Палачинки со јаворов сируп", "price": 38, "calories": 550, "protein": 12},
        {"name": "Мусли со млеко", "price": 32, "calories": 450, "protein": 10},
        {"name": "Тост со путер од кикирики", "price": 30, "calories": 420, "protein": 14},
        {"name": "Француски тост", "price": 35, "calories": 480, "protein": 10},
        {"name": "Јајца со сланина (3 јајца)", "price": 42, "calories": 650, "protein": 28},
        {"name": "Сендвич со пилешко", "price": 38, "calories": 600, "protein": 25}
    ],
    "lunch": [
        {"name": "Грав + пченка", "price": 55, "calories": 550, "protein": 18},
        {"name": "Пилешко со ориз", "price": 60, "calories": 580, "protein": 25},
        {"name": "Тестенини", "price": 50, "calories": 600, "protein": 20},
        {"name": "Полнета пиперка", "price": 48, "calories": 520, "protein": 15},
        {"name": "Сендвич топол", "price": 35, "calories": 420, "protein": 12},
        {"name": "Супа + леб", "price": 30, "calories": 350, "protein": 8},
        {"name": "Пилешка салата", "price": 52, "calories": 450, "protein": 28},
        {"name": "Риба со зеленчук", "price": 58, "calories": 520, "protein": 32},
        {"name": "Бургер со помфрит", "price": 60, "calories": 750, "protein": 22},
        {"name": "Лазањи", "price": 55, "calories": 680, "protein": 24},
        {"name": "Пица парче", "price": 48, "calories": 650, "protein": 18},
        {"name": "Свинско печено", "price": 55, "calories": 620, "protein": 30},
        {"name": "Шницла со помфрит", "price": 60, "calories": 900, "protein": 35},
        {"name": "Паста карбонара", "price": 55, "calories": 850, "protein": 22},
        {"name": "Ќебапи со леб", "price": 55, "calories": 800, "protein": 28},
        {"name": "Печено пиле со компири", "price": 60, "calories": 750, "protein": 32},
        {"name": "Тавче гравче", "price": 50, "calories": 700, "protein": 20},
        {"name": "Полнети пиперки со месо", "price": 55, "calories": 720, "protein": 25}
    ],
    "dinner": [
        {"name": "Салата со туна", "price": 35, "calories": 280, "protein": 22},
        {"name": "Омлет со зеленчук", "price": 30, "calories": 320, "protein": 16},
        {"name": "Сендвич + ајвар", "price": 25, "calories": 380, "protein": 9},
        {"name": "Јогурт + овошје", "price": 30, "calories": 250, "protein": 14},
        {"name": "Супа од домати", "price": 22, "calories": 200, "protein": 5},
        {"name": "Печен леб со сирење", "price": 20, "calories": 300, "protein": 10},
        {"name": "Салата од домати", "price": 15, "calories": 120, "protein": 3},
        {"name": "Грил пилешко со салата", "price": 42, "calories": 400, "protein": 35},
        {"name": "Вегетаријанска пита", "price": 38, "calories": 450, "protein": 12},
        {"name": "Торта од јаболка", "price": 30, "calories": 500, "protein": 5},
        {"name": "Тунис салата", "price": 35, "calories": 350, "protein": 18},
        {"name": "Печурки на жар", "price": 28, "calories": 220, "protein": 8},
        {"name": "Риба на скара со компири", "price": 44, "calories": 550, "protein": 40},
        {"name": "Пилешки бутчиња", "price": 38, "calories": 500, "protein": 35}
    ]
}

def find_meal(meal_type, max_price, target_calories, goal, remaining_budget=120):
    available = MEALS.get(meal_type, [])
    
    affordable = [m for m in available if m['price'] <= max_price and m['price'] <= remaining_budget]
    
    if not affordable:
        affordable = sorted(available, key=lambda x: x['price'])[:5]
    
    if goal == 'weight_loss':
        affordable.sort(key=lambda x: x['calories'])
        best_options = affordable[:3]
        return random.choice(best_options) if best_options else affordable[0]
    elif goal == 'muscle_gain':
        affordable.sort(key=lambda x: x['calories'], reverse=True)
        best_options = affordable[:3]
        return random.choice(best_options) if best_options else affordable[0]
    else:
        affordable.sort(key=lambda x: abs(x['calories'] - target_calories))
        best_options = affordable[:3]
        return random.choice(best_options) if best_options else affordable[0]

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/history')
@login_required
def history_page():
    return render_template('history.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        height = float(request.form.get('height', 170))
        weight = float(request.form.get('weight', 70))
        age = int(request.form.get('age', 20))
        gender = request.form.get('gender', 'male')
        goal = request.form.get('goal', 'maintain')
        
        if User.query.filter_by(username=username).first():
            flash('Корисничкото име веќе постои!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Емаил адресата веќе се користи!', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        daily_calories = calculate_bmr(height, weight, age, gender, goal)
        
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            height=height,
            weight=weight,
            age=age,
            gender=gender
        )
        
        new_user.preferences = json.dumps({
            'budget': 120,
            'goal': goal,
            'daily_calories': daily_calories
        })
        
        db.session.add(new_user)
        db.session.commit()
        
        if goal == 'weight_loss':
            kcal_message = f'Твоите дневни потреби за слабеење се {daily_calories} kcal (намалени за 400 kcal).'
        elif goal == 'muscle_gain':
            kcal_message = f'Твоите дневни потреби за зголемување маса се {daily_calories} kcal (зголемени за 400 kcal).'
        else:
            kcal_message = f'Твоите дневни потреби за одржување се {daily_calories} kcal.'
        
        flash(f'Успешно се регистриравте!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Погрешно корисничко име или лозинка!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        email = request.form.get('email')
        goal = request.form.get('goal')
        
        current_user.email = email
        prefs = json.loads(current_user.preferences or '{}')
        prefs['goal'] = goal
        
        new_daily_calories = calculate_bmr(current_user.height, current_user.weight, current_user.age, current_user.gender, goal)
        prefs['daily_calories'] = new_daily_calories
        
        current_user.preferences = json.dumps(prefs)
        db.session.commit()
        
        flash('Профилот е ажуриран!', 'success')
        return redirect(url_for('profile'))
    
    prefs = json.loads(current_user.preferences or '{}')
    return render_template('profile.html', user=current_user, prefs=prefs)

@app.route('/generate', methods=['POST'])
@login_required
def generate():
    data = request.get_json()
    goal = data.get('goal', 'maintain')
    
    prefs = json.loads(current_user.preferences or '{}')
    daily_budget = 120
    
    daily_calories_goal = calculate_bmr(current_user.height, current_user.weight, current_user.age, current_user.gender, goal)
    
    calories_per_meal = {
        'breakfast': round(daily_calories_goal * 0.25),
        'lunch': round(daily_calories_goal * 0.45),
        'dinner': round(daily_calories_goal * 0.30)
    }
    
    remaining = daily_budget
    meals = {}
    
    max_breakfast = min(45, remaining - 60)
    meals['breakfast'] = find_meal('breakfast', max_breakfast, calories_per_meal['breakfast'], goal, remaining)
    remaining -= meals['breakfast']['price']
    
    max_lunch = min(70, remaining - 20)
    if max_lunch < 40:
        max_lunch = remaining - 20
    meals['lunch'] = find_meal('lunch', max_lunch, calories_per_meal['lunch'], goal, remaining)
    remaining -= meals['lunch']['price']
    
    meals['dinner'] = find_meal('dinner', remaining, calories_per_meal['dinner'], goal, remaining)
    
    total_price = sum(m['price'] for m in meals.values())
    total_calories = sum(m['calories'] for m in meals.values())
    
    if total_price > daily_budget:
        for mtype in ['lunch', 'breakfast', 'dinner']:
            available = MEALS.get(mtype, [])
            cheaper = [m for m in available if m['price'] <= meals[mtype]['price'] - 5]
            if cheaper:
                cheaper.sort(key=lambda x: x['price'])
                meals[mtype] = cheaper[0]
                total_price = sum(m['price'] for m in meals.values())
                if total_price <= daily_budget:
                    break
    
    total_price = sum(m['price'] for m in meals.values())
    total_calories = sum(m['calories'] for m in meals.values())
    
    prefs['goal'] = goal
    prefs['daily_calories'] = daily_calories_goal
    current_user.preferences = json.dumps(prefs)
    db.session.commit()
    
    history = MealPlanHistory(
        user_id=current_user.id,
        breakfast=meals['breakfast']['name'],
        lunch=meals['lunch']['name'],
        dinner=meals['dinner']['name'],
        snack=None,
        snack_calories=0,
        snack_price=0,
        total_price=total_price,
        total_calories=total_calories,
        budget=daily_budget,
        goal=goal
    )
    db.session.add(history)
    db.session.commit()
    
    if goal == 'weight_loss':
        if total_calories <= daily_calories_goal:
            calorie_status = f"✅ За слабеење: {total_calories}/{daily_calories_goal} kcal ({(daily_calories_goal - total_calories)} kcal помалку)"
        else:
            calorie_status = f"⚠️ За слабеење: {total_calories}/{daily_calories_goal} kcal. Пробај со помали порции."
    elif goal == 'muscle_gain':
        if total_calories >= daily_calories_goal:
            calorie_status = f"💪 За мускули: {total_calories}/{daily_calories_goal} kcal (+{total_calories - daily_calories_goal} kcal повеќе)"
        else:
            calorie_status = f"⚠️ За мускули: {total_calories}/{daily_calories_goal} kcal. Додади уште нешто."
    else:
        if daily_calories_goal - 100 <= total_calories <= daily_calories_goal + 100:
            calorie_status = f"⚖️ За одржување: {total_calories}/{daily_calories_goal} kcal (одличен баланс)"
        elif total_calories < daily_calories_goal:
            calorie_status = f"⚖️ За одржување: {total_calories}/{daily_calories_goal} kcal (малку помалку)"
        else:
            calorie_status = f"⚖️ За одржување: {total_calories}/{daily_calories_goal} kcal (малку повеќе)"
    
    if total_price <= daily_budget:
        diff = daily_budget - total_price
        calorie_status += f" 💰 Во буџет: {total_price}/120 ден. Остаток: {diff} ден."
    else:
        diff = total_price - daily_budget
        calorie_status += f" ⚠️ Над буџет за {diff} ден."
    
    return jsonify({
        'plan': meals,
        'total_price': total_price,
        'total_calories': total_calories,
        'daily_calories_goal': daily_calories_goal,
        'daily_budget': daily_budget,
        'within_budget': total_price <= daily_budget,
        'calorie_status': calorie_status
    })

@app.route('/track_meal', methods=['POST'])
@login_required
def track_meal():
    try:
        data = request.get_json()
        new_meal = MealEntry(
            user_id=current_user.id,
            meal_type=data.get('meal_type'),
            meal_name=data.get('meal_name'),
            calories=data.get('calories'),
            price=data.get('price'),
            date=date.today()
        )
        db.session.add(new_meal)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print("Грешка:", str(e))
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/add_snack', methods=['POST'])
@login_required
def add_snack():
    try:
        data = request.get_json()
        meal_name = data.get('meal_name')
        
        found_meal = None
        for meal_type in ['breakfast', 'lunch', 'dinner']:
            for meal in MEALS[meal_type]:
                if meal['name'] == meal_name:
                    found_meal = meal
                    break
            if found_meal:
                break
        
        if found_meal:
            new_snack = MealEntry(
                user_id=current_user.id,
                meal_type='snack',
                meal_name=found_meal['name'],
                calories=found_meal['calories'],
                price=found_meal['price'],
                date=date.today()
            )
            db.session.add(new_snack)
            
            today_history = MealPlanHistory.query.filter_by(
                user_id=current_user.id, 
                date=date.today()
            ).first()
            
            if today_history:
                today_history.snack = found_meal['name']
                today_history.snack_calories = found_meal['calories']
                today_history.snack_price = found_meal['price']
                today_history.total_price += found_meal['price']
                today_history.total_calories += found_meal['calories']
            else:
                new_history = MealPlanHistory(
                    user_id=current_user.id,
                    breakfast="Нема",
                    lunch="Нема",
                    dinner="Нема",
                    snack=found_meal['name'],
                    snack_calories=found_meal['calories'],
                    snack_price=found_meal['price'],
                    total_price=found_meal['price'],
                    total_calories=found_meal['calories'],
                    budget=120,
                    goal=json.loads(current_user.preferences or '{}').get('goal', 'maintain'),
                    date=date.today()
                )
                db.session.add(new_history)
            
            db.session.commit()
            return jsonify({'success': True, 'meal': found_meal})
        else:
            return jsonify({'success': False, 'error': 'Оброкот не е пронајден'})
    except Exception as e:
        print("Грешка:", str(e))
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_all_meals')
@login_required
def get_all_meals():
    all_meals = []
    for meal_type, meals in MEALS.items():
        for meal in meals:
            all_meals.append({
                'name': meal['name'],
                'price': meal['price'],
                'calories': meal['calories'],
                'protein': meal.get('protein', 0),
                'type': meal_type
            })
    return jsonify(all_meals)

@app.route('/get_today_meals')
@login_required
def get_today_meals():
    meals = MealEntry.query.filter_by(user_id=current_user.id, date=date.today()).all()
    return jsonify([{
        'meal_type': m.meal_type,
        'meal_name': m.meal_name,
        'calories': m.calories,
        'price': m.price
    } for m in meals])

@app.route('/get_history')
@login_required
def get_history():
    history = MealPlanHistory.query.filter_by(user_id=current_user.id).order_by(MealPlanHistory.date.desc()).limit(10).all()
    return jsonify([{
        'breakfast': h.breakfast,
        'lunch': h.lunch,
        'dinner': h.dinner,
        'snack': h.snack if h.snack else None,
        'snack_calories': h.snack_calories,
        'snack_price': h.snack_price,
        'total_price': h.total_price,
        'total_calories': h.total_calories,
        'date': h.date.strftime('%d.%m.%Y')
    } for h in history])

@app.route('/get_recommendations')
@login_required
def get_recommendations():
    prefs = json.loads(current_user.preferences or '{}')
    goal = prefs.get('goal', 'maintain')
    daily_calories_goal = calculate_bmr(current_user.height, current_user.weight, current_user.age, current_user.gender, goal)
    
    recommendations = []
    recommendations.append({
        'title': '💰 Неделен буџет',
        'description': 'Твојот неделен буџет е 840 денари (120 денари на ден).',
        'price': ''
    })
    
    today_meals = MealEntry.query.filter_by(user_id=current_user.id, date=date.today()).all()
    consumed = sum(m.calories for m in today_meals)
    remaining = daily_calories_goal - consumed
    
    if goal == 'weight_loss':
        recommendations.append({
            'title': '🥗 За слабеење',
            'description': f'Твојата цел е {daily_calories_goal} kcal на ден. Ова е 400 kcal помалку од одржување.',
            'price': ''
        })
        if remaining > 0:
            recommendations.append({
                'title': '🔥 Калории',
                'description': f'Уште можеш да внесеш {remaining} kcal денес.',
                'price': ''
            })
    elif goal == 'muscle_gain':
        recommendations.append({
            'title': '💪 За мускули',
            'description': f'Твојата цел е {daily_calories_goal} kcal на ден. Ова е 400 kcal повеќе од одржување.',
            'price': ''
        })
        recommendations.append({
            'title': '🥚 Совет',
            'description': 'Додади повеќе протеини (јајца, месо) за подобри резултати!',
            'price': '+~30 ден.'
        })
        if remaining > 0:
            recommendations.append({
                'title': '🔥 Калории',
                'description': f'Треба да внесеш уште {remaining} kcal за да ја достигнеш целта.',
                'price': ''
            })
    else:
        recommendations.append({
            'title': '⚖️ За одржување',
            'description': f'Твојата цел е {daily_calories_goal} kcal на ден.',
            'price': ''
        })
    
    if remaining < 0:
        recommendations.append({
            'title': '⚠️ Внимание',
            'description': f'Ги надмина калориите за {abs(remaining)} kcal.',
            'price': ''
        })
    
    return jsonify(recommendations)

@app.route('/get_preferences')
@login_required
def get_preferences():
    prefs = json.loads(current_user.preferences or '{}')
    daily_calories = calculate_bmr(
        current_user.height, current_user.weight, current_user.age, current_user.gender,
        prefs.get('goal', 'maintain')
    )
    return jsonify({
        'budget': prefs.get('budget', 120),
        'goal': prefs.get('goal', 'maintain'),
        'daily_calories': daily_calories
    })

@app.route('/save_preferences', methods=['POST'])
@login_required
def save_preferences():
    data = request.get_json()
    prefs = json.loads(current_user.preferences or '{}')
    prefs['goal'] = data.get('goal', 'maintain')
    
    new_daily_calories = calculate_bmr(
        current_user.height, current_user.weight, current_user.age, current_user.gender,
        prefs['goal']
    )
    prefs['daily_calories'] = new_daily_calories
    
    current_user.preferences = json.dumps(prefs)
    db.session.commit()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True)