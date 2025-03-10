# Import the necessary libraries
from statistics import mode
from flask import Flask, render_template, request, redirect, url_for, session
import numpy as np
import pandas as pd
import os
from scipy.stats import mode
from sklearn.svm import SVC
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier
import joblib
import pickle
import warnings
from sklearn.exceptions import DataConversionWarning
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

from flask_sqlalchemy import SQLAlchemy
import mysql.connector

# load the training and testing dataset
train_data = pd.read_csv("models/Training.csv").dropna(axis=1)
test_data = pd.read_csv("models/Testing.csv").dropna(axis=1)

encoder = LabelEncoder()
train_data["prognosis"] = encoder.fit_transform(train_data["prognosis"])

X = train_data.iloc[:, :-1]
y = train_data.iloc[:, -1]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=24
)


def cv_scoring(estimator, X, y):
    return accuracy_score(y, estimator.predict(X))


models = {
    "SVC": SVC(),
    "Gaussian NB": GaussianNB(),
    "Random Forest": RandomForestClassifier(random_state=18),
}

# producing cross validation score for models
for model_name in models:
    model = models[model_name]
    scores = cross_val_score(model, X, y, cv=10, n_jobs=-1, scoring=cv_scoring)

svm_model = SVC()
svm_model.fit(X_train, y_train)
preds = svm_model.predict(X_test)

nb_model = GaussianNB()
nb_model.fit(X_train, y_train)
preds = nb_model.predict(X_test)

rf_model = RandomForestClassifier(random_state=18)
rf_model.fit(X_train, y_train)
preds = rf_model.predict(X_test)

from statistics import mode

# Training the models on whole data
final_svm_model = SVC()
final_nb_model = GaussianNB()
final_rf_model = RandomForestClassifier(random_state=18)
final_svm_model.fit(X, y)
final_nb_model.fit(X, y)
final_rf_model.fit(X, y)

test_X = test_data.iloc[:, :-1]
test_Y = encoder.transform(test_data.iloc[:, -1])

svm_preds = final_svm_model.predict(test_X)
nb_preds = final_nb_model.predict(test_X)
rf_preds = final_rf_model.predict(test_X)

final_preds = [mode([i, j, k]) for i, j, k in zip(svm_preds, nb_preds, rf_preds)]

# Disable the warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=DataConversionWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Initializing Models
models = {
    "SVC": SVC(),
    "Gaussian NB": GaussianNB(),
    "Random Forest": RandomForestClassifier(random_state=18),
}

symptoms = X.columns.values

# Creating a symptom index dictionary to encode the
# input symptoms into numerical form
symptom_index = {}
for index, value in enumerate(symptoms):
    symptom = " ".join([i.capitalize() for i in value.split("_")])
    symptom_index[symptom] = index

data_dict = {"symptom_index": symptom_index, "predictions_classes": encoder.classes_}


# Defining the Function
# Input: string containing symptoms separated by commas
# Output: Generated predictions by models
def predictDisease(symptoms):
    symptoms = symptoms.split(",")

    # creating input data for the models
    input_data = [0] * len(data_dict["symptom_index"])
    for symptom in symptoms:
        if symptom in data_dict["symptom_index"]:
            index = data_dict["symptom_index"][symptom]
            input_data[index] = 1

    # reshaping the input data and converting it
    # into suitable format for model predictions
    input_data = np.array(input_data).reshape(1, -1)

    # generating individual outputs
    rf_prediction = data_dict["predictions_classes"][
        final_rf_model.predict(input_data)[0]
    ]
    nb_prediction = data_dict["predictions_classes"][
        final_nb_model.predict(input_data)[0]
    ]
    svm_prediction = data_dict["predictions_classes"][
        final_svm_model.predict(input_data)[0]
    ]

    # making final prediction by taking mode of all predictions
    final_prediction = mode([rf_prediction, nb_prediction, svm_prediction])
    predictions = {
        "RF model prediction": rf_prediction,
        "Naive Bayes prediction": nb_prediction,
        "SVM model prediction": svm_prediction,
        "Final prediction": final_prediction,
    }
    return predictions


# start flask application
app = Flask(__name__)

app.secret_key = "ash_key"
db = mysql.connector.connect(
    host="mysql", user="medical_user", password="medicalpass", database="medical"
)

# defining the different routes of the website
@app.route("/", methods=["GET", "POST"])
def registration():
    cursor = db.cursor()
    create_table_query = """
    CREATE TABLE IF NOT EXISTS patients (
        ID INT AUTO_INCREMENT PRIMARY KEY,
        Firstname VARCHAR(255) NOT NULL,
        Lastname VARCHAR(255) NOT NULL,
        Email VARCHAR(255) UNIQUE NOT NULL,
        Username VARCHAR(255) UNIQUE NOT NULL,
        CountryCode VARCHAR(10),
        PhoneNumber VARCHAR(20),
        Gender VARCHAR(10),
        Password VARCHAR(255) NOT NULL
    )
    """
    cursor.execute(create_table_query)
    db.commit()

    if request.method == "POST":
        if "login" in request.form:
            return redirect(url_for("login"))

        firstname = request.form["fname"]
        lastname = request.form["lname"]
        email = request.form["email"]
        username = request.form["username"]
        countrycode = request.form["country-code"]
        phonenumber = request.form["phone"]
        gender = request.form["gender"]
        password = request.form["password"]

        query = "INSERT INTO patients (Firstname, Lastname, Email, Username, CountryCode, PhoneNumber, Gender, Password) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        values = (
            firstname,
            lastname,
            email,
            username,
            countrycode,
            phonenumber,
            gender,
            password,
        )
        cursor.execute(query, values)
        db.commit()
        return redirect(url_for("login"))

    return render_template("patient-registration.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        cursor = db.cursor()
        query = "SELECT * FROM patients WHERE username = %s AND password = %s"
        values = (username, password)
        cursor.execute(query, values)
        user = cursor.fetchone()
        if user:
            session["username"] = username
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")


@app.route("/index")
def index():
    # require user to be logged in before accessing the platform
    if "username" in session:
        return render_template("index.html")
    else:
        return redirect(url_for("login"))


@app.route("/consultation")
def consultation():
    return render_template("consultation.html")


@app.route("/news")
def news():
    return render_template("news.html")


@app.route("/patient")
def patient():
    return render_template("patient.html")


@app.route("/predictor")
def predictor():
    return render_template("predictor.html")


@app.route("/predict", methods=["GET", "POST"])
def predict():
    if request.method == "POST":
        # Get the input data from the form
        symptom_list = request.form.getlist("symptoms")
        symptoms = ", ".join(symptom_list)
        # Make a prediction using the machine learning model
        prediction = predictDisease(symptoms)
        # Render a template with the prediction results
        return render_template("result.html", prediction=prediction)
    else:
        return render_template("predictor.html")


@app.route("/profile/<string:username>")
def profile(user_id):
    cursor = db.cursor()
    query = "SELECT * FROM users WHERE username = %s"
    values = (user_id,)
    cursor.execute(query, values)
    user = cursor.fetchone()
    return render_template("patient.html", user=user)


@app.route("/logout")
def logout():
    # Perform logout actions
    session.clear()  # Clear session data
    # Additional logout tasks
    return render_template("patient-registration.html")  # Redirect to registration page


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
