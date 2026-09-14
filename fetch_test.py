from flask import *
import sqlite3
import requests
connection = sqlite3.connect('destinations.db')
cursor = connection.cursor()
cursor.execute("SELECT name FROM countries")
country_row = cursor.fetchall()
print(country_row)
connection.close()