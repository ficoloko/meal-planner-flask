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

class UserMeal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meal_name = db.Column(db.String(100), nullable=False)
    meal_type = db.Column(db.String(20))
    price = db.Column(db.Integer)
    calories = db.Column(db.Integer)
    protein = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DailyPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    breakfast = db.Column(db.String(100))
    breakfast_price = db.Column(db.Integer)
    breakfast_calories = db.Column(db.Integer)
    lunch = db.Column(db.String(100))
    lunch_price = db.Column(db.Integer)
    lunch_calories = db.Column(db.Integer)
    dinner = db.Column(db.String(100))
    dinner_price = db.Column(db.Integer)
    dinner_calories = db.Column(db.Integer)
    date = db.Column(db.Date, default=date.today)
    custom_meals = db.Column(db.String(1000), default='[]')

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

def find_meal(meal_type, max_price, target_calories, goal, user_id, remaining_budget=120):
    available = MEALS.get(meal_type, []).copy()
    
    user_meals = UserMeal.query.filter_by(user_id=user_id, meal_type=meal_type).all()
    for meal in user_meals:
        available.append({
            'name': meal.meal_name,
            'price': meal.price,
            'calories': meal.calories,
            'protein': meal.protein,
            'is_custom': True
        })
    
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

@app.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    prefs = json.loads(current_user.preferences or '{}')
    if prefs.get('onboarding_complete', False):
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        height = float(request.form.get('height', 170))
        weight = float(request.form.get('weight', 70))
        age = int(request.form.get('age', 20))
        gender = request.form.get('gender', 'male')
        goal = request.form.get('goal', 'maintain')
        
        current_user.height = height
        current_user.weight = weight
        current_user.age = age
        current_user.gender = gender
        
        daily_calories = calculate_bmr(height, weight, age, gender, goal)
        
        prefs['goal'] = goal
        prefs['daily_calories'] = daily_calories
        prefs['onboarding_complete'] = True
        prefs['budget'] = 120
        
        current_user.preferences = json.dumps(prefs)
        db.session.commit()
        
        return redirect(url_for('home'))
    
    return render_template('onboarding.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Корисничкото име веќе постои!', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Емаил адресата веќе се користи!', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            height=170,
            weight=70,
            age=20,
            gender='male'
        )
        
        new_user.preferences = json.dumps({
            'budget': 120,
            'goal': 'maintain',
            'daily_calories': 2000,
            'onboarding_complete': False
        })
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Успешно се регистриравте! Сега најавете се.', 'success')
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
            prefs = json.loads(user.preferences or '{}')
            if not prefs.get('onboarding_complete', False):
                return redirect(url_for('onboarding'))
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
    breakfast_meal = find_meal('breakfast', max_breakfast, calories_per_meal['breakfast'], goal, current_user.id, remaining)
    meals['breakfast'] = {
        'name': breakfast_meal['name'],
        'price': breakfast_meal['price'],
        'calories': breakfast_meal['calories'],
        'protein': breakfast_meal.get('protein', 0),
        'is_custom': breakfast_meal.get('is_custom', False)
    }
    remaining -= breakfast_meal['price']
    
    max_lunch = min(70, remaining - 20)
    if max_lunch < 40:
        max_lunch = remaining - 20
    lunch_meal = find_meal('lunch', max_lunch, calories_per_meal['lunch'], goal, current_user.id, remaining)
    meals['lunch'] = {
        'name': lunch_meal['name'],
        'price': lunch_meal['price'],
        'calories': lunch_meal['calories'],
        'protein': lunch_meal.get('protein', 0),
        'is_custom': lunch_meal.get('is_custom', False)
    }
    remaining -= lunch_meal['price']
    
    dinner_meal = find_meal('dinner', remaining, calories_per_meal['dinner'], goal, current_user.id, remaining)
    meals['dinner'] = {
        'name': dinner_meal['name'],
        'price': dinner_meal['price'],
        'calories': dinner_meal['calories'],
        'protein': dinner_meal.get('protein', 0),
        'is_custom': dinner_meal.get('is_custom', False)
    }
    
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
                'type': meal_type,
                'is_custom': False
            })
    return jsonify(all_meals)

@app.route('/get_all_meals_for_planner')
@login_required
def get_all_meals_for_planner():
    all_meals = []
    
    for meal_type, meals in MEALS.items():
        for meal in meals:
            all_meals.append({
                'name': meal['name'],
                'price': meal['price'],
                'calories': meal['calories'],
                'protein': meal.get('protein', 0),
                'type': meal_type,
                'is_custom': False
            })
    
    custom_meals = UserMeal.query.filter_by(user_id=current_user.id).all()
    for meal in custom_meals:
        all_meals.append({
            'name': meal.meal_name,
            'price': meal.price,
            'calories': meal.calories,
            'protein': meal.protein,
            'type': meal.meal_type,
            'is_custom': True,
            'id': meal.id
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

@app.route('/get_exercise_recommendations')
@login_required
def get_exercise_recommendations():
    prefs = json.loads(current_user.preferences or '{}')
    goal = prefs.get('goal', 'maintain')
    
    from datetime import date
    day_of_week = date.today().weekday()  # 0=Понеделник, 6=Недела
    
    exercises = {
        'weight_loss': [
            [  # Понеделник
                {'exercise': 'Трчање', 'duration': '30 мин', 'calories_burn': '~300 kcal', 'tip': 'Трчај умерено темпо'},
                {'exercise': 'Скокање јаже', 'duration': '15 мин', 'calories_burn': '~180 kcal', 'tip': 'Одмори 30 сек на секои 3 мин'},
                {'exercise': 'Планк', 'duration': '3 x 45 сек', 'calories_burn': '~50 kcal', 'tip': 'Држи го грбот рамен'},
            ],
            [  # Вторник
                {'exercise': 'Велосипед', 'duration': '45 мин', 'calories_burn': '~350 kcal', 'tip': 'Одлична кардио активност'},
                {'exercise': 'Чучњеви', 'duration': '4 x 15', 'calories_burn': '~120 kcal', 'tip': 'Спуштај се подолу'},
                {'exercise': 'Берпи', 'duration': '3 x 10', 'calories_burn': '~100 kcal', 'tip': 'Одмори 1 мин меѓу серии'},
            ],
            [  # Среда
                {'exercise': 'Пливање', 'duration': '30 мин', 'calories_burn': '~250 kcal', 'tip': 'Нежно кон зглобовите'},
                {'exercise': 'Планинарење', 'duration': '60 мин', 'calories_burn': '~400 kcal', 'tip': 'Носи вода'},
                {'exercise': 'Истегнување', 'duration': '20 мин', 'calories_burn': '~60 kcal', 'tip': 'Задржи ја секоја позиција 30 сек'},
            ],
            [  # Четврток
                {'exercise': 'HIIT тренинг', 'duration': '20 мин', 'calories_burn': '~300 kcal', 'tip': '30 сек работа, 15 сек одмор'},
                {'exercise': 'Брзо одење', 'duration': '45 мин', 'calories_burn': '~200 kcal', 'tip': 'Брзо темпо цело време'},
                {'exercise': 'Склекови', 'duration': '4 x 12', 'calories_burn': '~80 kcal', 'tip': 'Полека надолу, брзо нагоре'},
            ],
            [  # Петок
                {'exercise': 'Трчање интервали', 'duration': '25 мин', 'calories_burn': '~320 kcal', 'tip': '1 мин брзо, 1 мин бавно'},
                {'exercise': 'Лунги', 'duration': '3 x 12', 'calories_burn': '~100 kcal', 'tip': 'Наизменично лева и десна нога'},
                {'exercise': 'Абдоминали', 'duration': '3 x 20', 'calories_burn': '~60 kcal', 'tip': 'Бавни и контролирани движења'},
            ],
            [  # Сабота
                {'exercise': 'Јога', 'duration': '45 мин', 'calories_burn': '~150 kcal', 'tip': 'Фокус на дишење'},
                {'exercise': 'Одење во природа', 'duration': '60 мин', 'calories_burn': '~250 kcal', 'tip': 'Активен одмор'},
                {'exercise': 'Истегнување', 'duration': '15 мин', 'calories_burn': '~40 kcal', 'tip': 'Превенција од повреди'},
            ],
            [  # Недела
                {'exercise': 'Лесно трчање', 'duration': '20 мин', 'calories_burn': '~180 kcal', 'tip': 'Бавно и уживачки'},
                {'exercise': 'Медитација + јога', 'duration': '30 мин', 'calories_burn': '~80 kcal', 'tip': 'Ден за опоравување'},
                {'exercise': 'Истегнување', 'duration': '15 мин', 'calories_burn': '~40 kcal', 'tip': 'Подготви се за новата недела'},
            ],
        ],
        'muscle_gain': [
            [  # Понеделник - Гради
                {'exercise': 'Склекови', 'duration': '4 x 12', 'calories_burn': '~100 kcal', 'tip': 'Гради и рамења'},
                {'exercise': 'Дипови', 'duration': '3 x 10', 'calories_burn': '~80 kcal', 'tip': 'Користи стол или клупа'},
                {'exercise': 'Планк', 'duration': '3 x 60 сек', 'calories_burn': '~60 kcal', 'tip': 'Стабилизација'},
            ],
            [  # Вторник - Нозе
                {'exercise': 'Чучњеви', 'duration': '4 x 15', 'calories_burn': '~150 kcal', 'tip': 'Длабоко до 90 степени'},
                {'exercise': 'Лунги', 'duration': '3 x 12', 'calories_burn': '~120 kcal', 'tip': 'Чекори нанапред'},
                {'exercise': 'Искок чучњеви', 'duration': '3 x 10', 'calories_burn': '~130 kcal', 'tip': 'Експлозивно движење'},
            ],
            [  # Среда - Одмор/Core
                {'exercise': 'Абдоминали', 'duration': '4 x 20', 'calories_burn': '~80 kcal', 'tip': 'Бавни движења'},
                {'exercise': 'Планк странично', 'duration': '3 x 30 сек', 'calories_burn': '~50 kcal', 'tip': 'Секоја страна'},
                {'exercise': 'Истегнување', 'duration': '20 мин', 'calories_burn': '~60 kcal', 'tip': 'Важно за опоравување'},
            ],
            [  # Четврток - Грб и рамења
                {'exercise': 'Потег нагоре', 'duration': '4 x 8', 'calories_burn': '~120 kcal', 'tip': 'Ако можеш, иначе негативни'},
                {'exercise': 'Пајк склекови', 'duration': '3 x 10', 'calories_burn': '~90 kcal', 'tip': 'Рамења напред'},
                {'exercise': 'Супермен', 'duration': '3 x 15', 'calories_burn': '~60 kcal', 'tip': 'Лежи и кревај грб'},
            ],
            [  # Петок - Цело тело
                {'exercise': 'Берпи', 'duration': '4 x 10', 'calories_burn': '~150 kcal', 'tip': 'Максимален интензитет'},
                {'exercise': 'Мртво дигање', 'duration': '4 x 8', 'calories_burn': '~180 kcal', 'tip': 'Грбот рамен цело време'},
                {'exercise': 'Скокови на кутија', 'duration': '3 x 10', 'calories_burn': '~120 kcal', 'tip': 'Меко слетување'},
            ],
            [  # Сабота - Раце
                {'exercise': 'Диамантски склекови', 'duration': '3 x 10', 'calories_burn': '~80 kcal', 'tip': 'Трицепси'},
                {'exercise': 'Потег со тесен фат', 'duration': '3 x 8', 'calories_burn': '~100 kcal', 'tip': 'Бицепси'},
                {'exercise': 'Дипови на стол', 'duration': '3 x 12', 'calories_burn': '~90 kcal', 'tip': 'Трицепси и рамења'},
            ],
            [  # Недела - Активен одмор
                {'exercise': 'Лесно одење', 'duration': '30 мин', 'calories_burn': '~120 kcal', 'tip': 'Активен одмор'},
                {'exercise': 'Јога', 'duration': '20 мин', 'calories_burn': '~70 kcal', 'tip': 'Флексибилност'},
                {'exercise': 'Истегнување', 'duration': '15 мин', 'calories_burn': '~40 kcal', 'tip': 'Мускулите растат во одмор'},
            ],
        ],
        'maintain': [
            [  # Понеделник
                {'exercise': 'Брзо одење', 'duration': '45 мин', 'calories_burn': '~200 kcal', 'tip': 'Одржи срцевиот ритам'},
                {'exercise': 'Склекови', 'duration': '3 x 10', 'calories_burn': '~70 kcal', 'tip': 'Одржување на силата'},
                {'exercise': 'Истегнување', 'duration': '10 мин', 'calories_burn': '~30 kcal', 'tip': 'После секој тренинг'},
            ],
            [  # Вторник
                {'exercise': 'Велосипед', 'duration': '30 мин', 'calories_burn': '~250 kcal', 'tip': 'Умерено темпо'},
                {'exercise': 'Чучњеви', 'duration': '3 x 12', 'calories_burn': '~100 kcal', 'tip': 'Одржување на нозете'},
                {'exercise': 'Планк', 'duration': '3 x 40 сек', 'calories_burn': '~50 kcal', 'tip': 'Стабилност'},
            ],
            [  # Среда
                {'exercise': 'Јога', 'duration': '30 мин', 'calories_burn': '~100 kcal', 'tip': 'Флексибилност и баланс'},
                {'exercise': 'Одење во природа', 'duration': '45 мин', 'calories_burn': '~180 kcal', 'tip': 'Уживај во природата'},
                {'exercise': 'Дишни вежби', 'duration': '10 мин', 'calories_burn': '~20 kcal', 'tip': 'Релаксација'},
            ],
            [  # Четврток
                {'exercise': 'Трчање', 'duration': '25 мин', 'calories_burn': '~240 kcal', 'tip': 'Умерено темпо'},
                {'exercise': 'Лунги', 'duration': '3 x 10', 'calories_burn': '~90 kcal', 'tip': 'Баланс и координација'},
                {'exercise': 'Абдоминали', 'duration': '3 x 15', 'calories_burn': '~50 kcal', 'tip': 'Јачина'},
            ],
            [  # Петок
                {'exercise': 'Пливање', 'duration': '30 мин', 'calories_burn': '~250 kcal', 'tip': 'Цело тело'},
                {'exercise': 'Истегнување', 'duration': '15 мин', 'calories_burn': '~40 kcal', 'tip': 'Флексибилност'},
                {'exercise': 'Медитација', 'duration': '10 мин', 'calories_burn': '~20 kcal', 'tip': 'Ментално здравје'},
            ],
            [  # Сабота
                {'exercise': 'Планинарење', 'duration': '90 мин', 'calories_burn': '~500 kcal', 'tip': 'Викенд активност'},
                {'exercise': 'Истегнување', 'duration': '15 мин', 'calories_burn': '~40 kcal', 'tip': 'После планинарење'},
                {'exercise': 'Јога', 'duration': '20 мин', 'calories_burn': '~70 kcal', 'tip': 'Релаксација'},
            ],
            [  # Недела
                {'exercise': 'Лесно одење', 'duration': '30 мин', 'calories_burn': '~120 kcal', 'tip': 'Активен одмор'},
                {'exercise': 'Истегнување', 'duration': '20 мин', 'calories_burn': '~50 kcal', 'tip': 'Подготви се за неделата'},
                {'exercise': 'Дишни вежби', 'duration': '10 мин', 'calories_burn': '~20 kcal', 'tip': 'Релаксација'},
            ],
        ]
    }
    
    days = ['Понеделник', 'Вторник', 'Среда', 'Четврток', 'Петок', 'Сабота', 'Недела']
    today_exercises = exercises[goal][day_of_week]
    today_name = days[day_of_week]
    
    result = []
    for ex in today_exercises:
        result.append({
            'title': f'🗓️ {today_name}',
            'exercise': ex['exercise'],
            'duration': ex['duration'],
            'calories_burn': ex['calories_burn'],
            'tip': ex['tip']
        })
    
    return jsonify(result)

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

@app.route('/add_user_meal', methods=['POST'])
@login_required
def add_user_meal():
    try:
        data = request.get_json()
        print("=== ДОДАВАЊЕ НА CUSTOM ОБРОК ===")
        print("Податоци:", data)
        
        new_meal = UserMeal(
            user_id=current_user.id,
            meal_name=data.get('meal_name'),
            meal_type=data.get('meal_type'),
            price=data.get('price'),
            calories=data.get('calories'),
            protein=data.get('protein', 0)
        )
        new_entry = MealEntry(
    user_id=current_user.id,
    meal_type=data.get('meal_type', 'custom'),
    meal_name=data.get('meal_name'),
    calories=data.get('calories'),
    price=data.get('price'),
    date=date.today()
)
        db.session.add(new_meal)
        
        today = date.today()
        today_history = MealPlanHistory.query.filter_by(user_id=current_user.id, date=today).first()
        
        if today_history:
            if today_history.snack:
                today_history.snack += f", {data.get('meal_name')}"
                today_history.snack_calories += data.get('calories')
                today_history.snack_price += data.get('price')
            else:
                today_history.snack = data.get('meal_name')
                today_history.snack_calories = data.get('calories')
                today_history.snack_price = data.get('price')
            today_history.total_price += data.get('price')
            today_history.total_calories += data.get('calories')
        else:
            new_history = MealPlanHistory(
                user_id=current_user.id,
                breakfast="Нема",
                lunch="Нема",
                dinner="Нема",
                snack=data.get('meal_name'),
                snack_calories=data.get('calories'),
                snack_price=data.get('price'),
                total_price=data.get('price'),
                total_calories=data.get('calories'),
                budget=120,
                goal=json.loads(current_user.preferences or '{}').get('goal', 'maintain'),
                date=today
            )
            db.session.add(new_history)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
@app.route('/get_user_meals')
@login_required
def get_user_meals():
    meals = UserMeal.query.filter_by(user_id=current_user.id).order_by(UserMeal.created_at.desc()).all()
    return jsonify([{
        'id': m.id,
        'meal_name': m.meal_name,
        'meal_type': m.meal_type,
        'price': m.price,
        'calories': m.calories,
        'protein': m.protein
    } for m in meals])

@app.route('/delete_user_meal/<int:meal_id>', methods=['DELETE'])
@login_required
def delete_user_meal(meal_id):
    try:
        meal = UserMeal.query.filter_by(id=meal_id, user_id=current_user.id).first()
        if meal:
            db.session.delete(meal)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Оброкот не е пронајден'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/save_daily_plan', methods=['POST'])
@login_required
def save_daily_plan():
    try:
        data = request.get_json()
        plan = data.get('plan')
        
        existing = DailyPlan.query.filter_by(user_id=current_user.id, date=date.today()).first()
        if existing:
            existing.breakfast = plan['breakfast']['name']
            existing.breakfast_price = plan['breakfast']['price']
            existing.breakfast_calories = plan['breakfast']['calories']
            existing.lunch = plan['lunch']['name']
            existing.lunch_price = plan['lunch']['price']
            existing.lunch_calories = plan['lunch']['calories']
            existing.dinner = plan['dinner']['name']
            existing.dinner_price = plan['dinner']['price']
            existing.dinner_calories = plan['dinner']['calories']
            existing.custom_meals = json.dumps(plan.get('custom_meals', []))
        else:
            new_plan = DailyPlan(
                user_id=current_user.id,
                breakfast=plan['breakfast']['name'],
                breakfast_price=plan['breakfast']['price'],
                breakfast_calories=plan['breakfast']['calories'],
                lunch=plan['lunch']['name'],
                lunch_price=plan['lunch']['price'],
                lunch_calories=plan['lunch']['calories'],
                dinner=plan['dinner']['name'],
                dinner_price=plan['dinner']['price'],
                dinner_calories=plan['dinner']['calories'],
                custom_meals=json.dumps(plan.get('custom_meals', [])),
                date=date.today()
            )
            db.session.add(new_plan)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print("Грешка:", str(e))
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_daily_plan')
@login_required
def get_daily_plan():
    plan = DailyPlan.query.filter_by(user_id=current_user.id, date=date.today()).first()
    if plan:
        return jsonify({
            'exists': True,
            'breakfast': {'name': plan.breakfast, 'price': plan.breakfast_price, 'calories': plan.breakfast_calories},
            'lunch': {'name': plan.lunch, 'price': plan.lunch_price, 'calories': plan.lunch_calories},
            'dinner': {'name': plan.dinner, 'price': plan.dinner_price, 'calories': plan.dinner_calories}
        })
    return jsonify({'exists': False})
    return jsonify({
    'exists': True,
    'breakfast': {'name': plan.breakfast, 'price': plan.breakfast_price, 'calories': plan.breakfast_calories},
    'lunch': {'name': plan.lunch, 'price': plan.lunch_price, 'calories': plan.lunch_calories},
    'dinner': {'name': plan.dinner, 'price': plan.dinner_price, 'calories': plan.dinner_calories},
    'custom_meals': json.loads(plan.custom_meals or '[]')
})

@app.route('/delete_today_history', methods=['POST'])
@login_required
def delete_today_history():
    try:
        data = request.get_json()
        target_date = data.get('date')
        if target_date:
            from datetime import datetime
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
            
            daily_plan = DailyPlan.query.filter_by(user_id=current_user.id, date=target_date_obj).first()
            if daily_plan:
                db.session.delete(daily_plan)
            
            history = MealPlanHistory.query.filter_by(user_id=current_user.id, date=target_date_obj).first()
            if history:
                db.session.delete(history)
            
            meals = MealEntry.query.filter_by(user_id=current_user.id, date=target_date_obj).all()
            for meal in meals:
                db.session.delete(meal)
            
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Нема датум'})
    except Exception as e:
        print("Грешка при бришење:", str(e))
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_calorie_data')
@login_required
def get_calorie_data():
    from datetime import timedelta
    last_7_days = []
    for i in range(6, -1, -1):
        day = date.today() - timedelta(days=i)
        meals = MealEntry.query.filter_by(user_id=current_user.id, date=day).all()
        total_calories = sum(m.calories for m in meals)
        last_7_days.append({
            'date': day.strftime('%d.%m'),
            'calories': total_calories
        })
    return jsonify(last_7_days)

if __name__ == '__main__':
    print("http://localhost:5000")
    app.run(debug=True)