from flask import Flask, request, render_template, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, AlgorithmForm, RegistrationForm
import json
from datetime import datetime
from flask_talisman import Talisman

#pip install flask flask-sqlalchemy flask-migrate flask-wtf wtforms werkzeug email_validator flask_talisman
#install extension "SQLite Viewer" for better database readability

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///traintrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

talisman = Talisman(
   app,
   content_security_policy={
      'default-src': "'self'",
       'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
       'script-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data:",
    },
    content_security_policy_nonce_in=['script-src', 'style-src'],
)
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class PastWorkout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'))
    day = db.Column(db.String(50))  
    workout_data = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goals = db.Column(db.String(50), nullable=False)  
    experience_level = db.Column(db.String(50), nullable=False)
    workout_data = db.Column(db.Text, nullable=False)  
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('plans', lazy=True))

class Day(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'))
    day_name = db.Column(db.String(50))
    
    exercises = db.relationship('Exercise', backref='day', lazy=True)

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey('day.id'))
    name = db.Column(db.String(100))

def init_db():
    with app.app_context():
        db.create_all()

def load_workouts():
    with open('workouts.json', 'r') as f:
        return json.load(f)

def assign_workout(goals, experience_level):
    workout_data = load_workouts()
    
 
    plan = workout_data.get(goals, {}).get(experience_level, {})

    if "workouts" in plan:
        return plan["workouts"]
    else:
        raise ValueError(f"Workout data missing for goal: {goals}, level: {experience_level}")


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/algorithm', methods=['GET', 'POST'])
def algorithm():
    if 'user_id' not in session:
        return redirect('/login') 
    
    form = AlgorithmForm()
    if form.validate_on_submit():
        goals = form.goals.data
        experience_level = form.experience_level.data

        plan = assign_workout(goals, experience_level)

        session['goals'] = goals
        session['experience_level'] = experience_level
        session['workout_days'] = plan

        return render_template('result.html', workout_days=plan, days=len(plan))

    return render_template('algorithm.html', form=form)



@app.route('/save_plan', methods=['POST'])
def save_plan():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    workout_days = session.get('workout_days')
    goals = session.get('goals')
    experience_level = session.get('experience_level')


    workout_json = json.dumps(workout_days) 

    new_plan = Plan(user_id=user_id, goals=goals, experience_level=experience_level, workout_data=workout_json)
    db.session.add(new_plan)
    db.session.commit()

    return redirect('/my_plans')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data

        if User.query.filter_by(email=email).first():
            return "User already exists!"

        new_user = User(name=name, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect('/')

        return "Invalid email or password!"

    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/my_plans')
def my_plans():
    if 'user_id' not in session:
        return redirect('/login')

    user_plans = Plan.query.filter_by(user_id=session['user_id']).order_by(Plan.timestamp.desc()).all()

    for plan in user_plans:
    
        plan.workout_data = json.loads(plan.workout_data)

    return render_template('my_plans.html', plans=user_plans)

@app.route('/clear_plans', methods=['POST'])
def clear_plans():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    Plan.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return redirect('/my_plans')



@app.route('/get_plan_days/<int:plan_id>')
def get_plan_days(plan_id):
    days = Day.query.filter_by(plan_id=plan_id).all()
    return jsonify({"days": [{"id": day.id, "day_name": day.day_name} for day in days]})

@app.route('/get_plan_exercises/<int:day_id>')
def get_plan_exercises(day_id):
    exercises = Exercise.query.filter_by(day_id=day_id).all()
    return jsonify([{"id": exercise.id, "name": exercise.name} for exercise in exercises])

@app.route('/save_workout', methods=['POST'])
def save_workout():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    plan_id = request.form.get("plan_id")
    day_name = request.form.get("day")  
    
    plan = Plan.query.get(plan_id)
    if not plan:
        return "Plan not found", 404

    workout_data = {day_name: {"exercises": {}}} 
    
 
    exercises = json.loads(plan.workout_data).get(day_name, {}).get("exercises", [])
    for exercise in exercises:
        reps = request.form.get(f"{exercise}_reps")
        weight = request.form.get(f"{exercise}_weight")
        if reps and weight:  
            workout_data[day_name]["exercises"][exercise] = {
                "reps": int(reps),
                "weight": float(weight)
            }

 
    cardio_time = request.form.get("cardio_time")
    if cardio_time and cardio_time.isdigit():  
        workout_data[day_name]["cardio"] = {"time": int(cardio_time)}


  
    new_workout = PastWorkout(
        user_id=user_id,
        plan_id=plan_id,
        day=day_name,  
        workout_data=json.dumps(workout_data)  
    )
    db.session.add(new_workout)
    db.session.commit()

    return redirect('/past_workouts')


@app.route('/past_workouts')
def past_workouts():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    past_workouts = PastWorkout.query.filter_by(user_id=user_id).order_by(PastWorkout.timestamp.desc()).all()

    for workout in past_workouts:
        try:
            workout.workout_data = json.loads(workout.workout_data) 
        except json.JSONDecodeError:
            print(f"Error decoding workout_data for workout {workout.id}")

    return render_template('past_workouts.html', past_workouts=past_workouts)



@app.route('/clear_past_workouts', methods=['POST'])
def clear_past_workouts():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    PastWorkout.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return redirect('/past_workouts')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
