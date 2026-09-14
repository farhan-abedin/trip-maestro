import os
from dotenv import load_dotenv

load_dotenv()

from flask import *
import sqlite3
import requests
from datetime import *
import json


app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]  

class TripAdvisorAPI: #defines class
    def __init__(self): #initializes class
        self.api_key = os.environ["TRIPADVISOR_API_KEY"] #API key attribute
        self.base_url = "https://api.content.tripadvisor.com/api/v1/location" #Base URL for API
        self.headers = {"accept": "application/json"} #Common headers used for API calls

    def search_destinations(self, country_name): #Method to search for destinations
        search_url = f"{self.base_url}/search?key={self.api_key}&searchQuery={country_name}&category=geos&language=en" #URL for search endpoint
        response = requests.get(search_url, headers=self.headers) # Sends request to API
        if response.status_code == 200: #If the request is successful
            data = response.json() #Converts response to JSON
            first_item = data['data'][0]  #Looks into the data variable, for the data section of response, for first item
            location_id = first_item.get('location_id')  #Extract the location ID
            name = first_item.get('name')  #Extract the name
            return location_id, name #Returns location ID and name
        else: #If request is unsuccessful
            print(f"Error fetching destinations: {response.status_code}") #Prints error message
            return None, None #Returns nothing for both location ID and name

    def get_location_details(self, location_id): #Method to get location details
        details_url = f"{self.base_url}/{location_id}/details?key={self.api_key}&language=en" #URL for details endpoint
        response = requests.get(details_url, headers=self.headers) #Sends request to API
        if response.status_code == 200:
            data = response.json()
            description = data.get('description', 'No description available') #Extracts description from data
            web_url = data.get('web_url', 'No web URL available') #Extracts web URL from data
            return description, web_url
        else:
            print(f"Error fetching location details: {response.status_code}")
            return None, None

    def get_location_image(self, location_id): #Method to get location image
        images_url = f"{self.base_url}/{location_id}/photos?key={self.api_key}&language=en"
        response = requests.get(images_url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            images = data.get('data', []) #Extracts images from data
            first_image = images[0] #Extracts first image from images
            medium_image = first_image.get('images', {}).get('medium', {}) #Extracts all types of the first image
            # then the middle image from there
            image_url = medium_image.get('url', 'No image URL available') #Extracts image URL from medium image
            return image_url
        else:
            print(f"Error fetching location images: {response.status_code}")
            return []

    def fetch_and_display_details(self, country_name): #Method to fetch and display details
        location_id, name = self.search_destinations(country_name) #Searches for destinations
        description, web_url = self.get_location_details(location_id) #Gets location details
        image_url = self.get_location_image(location_id) #Gets location image
        return name, description, web_url, image_url #Returns name, description, web URL, and image URL

def determinePreferences():
    userConnection = sqlite3.connect('users.db') #Same old database connection
    try:
        userCursor = userConnection.cursor()
        userCursor.execute("SELECT explorativeRating, isolatedRating, uniqueCuisineRating FROM users WHERE id = ?", 
                    (session['user_id'],)) #Gets user preferences from database
        user_prefs = userCursor.fetchone() #Takes the user's record from the database
    finally:
        userConnection.close() #Ends connection between program and database to avoid locking

    explore_pref = user_prefs[0] * 0.1  #Converts user preferences to a multiplier of each destinations score
    peaceful_pref = user_prefs[1] * 0.05
    cuisine_pref = user_prefs[2] * 0.1

    destConnection = sqlite3.connect('users.db') 
    try:
        destCursor = destConnection.cursor()
        destCursor.execute("SELECT * FROM countries")
        countries = destCursor.fetchall() #Makes a complete array of every country in the database
    finally:
        destConnection.close()
    ranking = [] #Makes an empty array to store the rankings of the numerical scores
    destRanking = [] #Makes an empty array to store the rankings of the countries
    scoreDict = {} #Makes a dictionary to hold scores and their corresponding countries
    for each in countries:
        score = round(each[1] * cuisine_pref + each[2] * peaceful_pref + each[3] * explore_pref)
        #Calculates the score of each country based on user preferences
        if score not in scoreDict: #If the score is not already in the dictionary
            scoreDict[score] = each[0] #Adds the score and country to the dictionary
        else: #If the score is already in the dictionary
            while score in scoreDict: #Makes sure that it doesn't increment to another score
                score += 0.01 #Increments the score by a small amount
            scoreDict[score] = each[0] #Adds the score and country to the dictionary
        ranking.append(score) #Adds that country's scr to the ranking array
        ranking.sort()  #Sorts the ranking array
        ranking.reverse() #Reverses the ranking array so that the highest score is first
    for each in ranking: #Goes through each score in the ranking array to rank the countries
        destRanking.append(scoreDict[each]) #Adds the country to the destRanking array based on the score
    return destRanking #Returns the array of countries ranked by user preferences
        
@app.route('/') #Run for a blank URL, e.g: www.tripmaestro.com/ 
def baseRoute(): 
    return render_template('login.html') #Returns user to login page

@app.route('/login', methods=['GET', 'POST']) #Run for what would be www.tripmaestro.com/login 
#These specify what HTTP methods this route can accept, GET meaning it can request data, and POST meaning it can send data for processing

def login():
    if request.method == 'POST': #Checks that a form has actually been submitted where data has been sent, rather than just changing the URL
        username = request.form['username'] #Defines 'username' with what was inputted in with the label of 'username' in the form
        password = request.form['password'] #Same as above but for the variable 'passowrd' and the label of 'password' in the HTML
        userConnection = sqlite3.connect('users.db') #Creates an instance of the database
        try:
            cursor = userConnection.cursor() #Creates a cursor that the program can use to interact with the database
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,)) #Gets all of the data from a matching username in the database
            user = cursor.fetchone() #This takes a record from the database and assigns it to user.
        finally:
            userConnection.close() #Ends userConnection between program and database 

        if user and user[2] == password: #Checks if user exists and inputted password matches what is in the database
            session['user_id'] = user[0] #Takes ID from database and enters it into the session to make future requests easier
            session['username'] = user[1] #Does same thing with username as some things are easier to request with username
            return redirect(url_for('dashboard')) #Redirects user to their dashboard (www.tripmaestro.com/dashboard) now logged in
        else:
            flash('Invalid username or password. Please try again.') #Password doesn't match, that is indicated to the user with a pop-up

    return render_template('login.html') #Makes a default point for if the URL was typed in manually for www.../login or another error

# Register route
@app.route('/register', methods=['GET', 'POST']) #Enables GET and POST methods for Python to send and receive data from the webpage
def register():
    if request.method == 'POST': #Checks that data has been received
        username = request.form['username'] #Defines username with what was entered in 'username' on the webpage
        password = request.form['password'] #Defines password with what was entered in 'password' on the webpage
        confirm_password = request.form['confirm_password'] #Defines confirm_password with what was entered as the 2nd password
        explorative_rating = request.form['explorativeRating'] #Defines explorative_rating with value from webpage
        isolated_rating = request.form['isolatedRating'] #Defines isolated_rating with value from webpage
        unique_cuisine_rating = request.form['uniqueCuisineRating'] #Defines unique_cuisine_rating with value from webpage

        if password != confirm_password: #Checks that the passwords are the same
            flash('Passwords do not match!') #Sends a pop-up to the user saying passwords do not match
            return redirect(url_for('register')) #Sends the user back to the registration page to try again
        try:
            userConnection = sqlite3.connect('users.db') #Same database userConnection as login system
            cursor = userConnection.cursor()
            cursor.execute(f"INSERT INTO users (username, password, explorativeRating, isolatedRating, uniqueCuisineRating) VALUES ('{username}', '{password}', {explorative_rating}, {isolated_rating}, {unique_cuisine_rating})") #Uses SQL to add new user to database
            userConnection.commit()
            userConnection.close()
            return redirect(url_for('login')) #Takes user to login            
        except sqlite3.IntegrityError: #Considers the error of a duplicate username
            flash('Username already exists. Please choose a different one.') #Gives a pop-up to the user indicating an error
        finally:
            userConnection.close()

    return render_template('register.html') #If webpage opened directly (with no form filled in), user redirected to that webpage

@app.route('/logout')
def logout():
    session.clear() #Clears all details held about user
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session: #If the user is not logged in
        return redirect(url_for('login')) #Redirects user to login page    
    
    holidayConnection = sqlite3.connect('users.db') #Creates dropdown list of holidays
    try:
        holidayCursor = holidayConnection.cursor()
        holidayCursor.execute("""
            SELECT holidayID, holidayTitle, countryName 
            FROM holidays 
            WHERE userID = ?
            """, (session['user_id'],))
        user_holidays = [] #Creates an empty array to store the user's holidays
        for row in holidayCursor.fetchall():
            user_holidays.append({'id': row[0], 'title': row[1], 'destination': row[2]})

    finally:
        holidayConnection.close()

    tripadvisorapi = TripAdvisorAPI() #Creates an instance of the TripAdvisorAPI class
    ranked_destinations = determinePreferences() #Gets array of ranked destinations
    page = request.args.get('page', 1, type=int) #Gets the page number from the URL, defaults to 1
    prev_page, next_page = page, page #Initializes variables for previous and next page
    per_page = 4 #Constant used to determine how many destinations are shown on each page
    start_index = (page - 1) * per_page #Finds first destination to be shown on a page
    end_index = start_index + per_page  #Finds last destination to be shown on a page
    page_items = [] #Creates an array to store dictionaries of destination data
    for each in range(start_index, end_index): #Goes through each destination in the range of destinations to be shown on the page
        name, description, web_url, image_url = tripadvisorapi.fetch_and_display_details(ranked_destinations[each])
        #Gets the name, description, web URL, and image URL of each destination
        page_items.append({'name': name, 'description': description, 'web_url': web_url, 'image_url': image_url})
        #Adds the name, description, web URL, and image URL to the page_items array
    if end_index < len(ranked_destinations): #If the end index is less than the total number of destinations
        next_page = page + 1 #Sets the next page to the current page plus 1
    if page > 1: #If the page is greater than 1
        prev_page = page - 1 #There has to be a page before it so set it to be that

    return render_template("dashboard.html",
                           page_items=page_items,
                           page=page,
                           next_page=next_page,
                           prev_page=prev_page,
                           user_holidays=user_holidays)

@app.route('/new_holiday', methods=['GET', 'POST']) #Expects form submission so needs both GET and POST methods
def new_holiday():
    if 'user_id' not in session: #If the user is not logged in
        return redirect(url_for('login')) #Redirects user to login page  
    if request.method == 'POST': #If the form has been submitted
        destination = request.form['destination']
        startDate = request.form['start-date']
        endDate = request.form['end-date']
        holiday_title = request.form['holiday-title'] 
        userID = session['user_id'] #Gets all data to be stored in database
        if not destination or not startDate or not endDate or not holiday_title: #If any fields are empty
            flash('Please fill in all fields')
            return render_template('new_holiday.html', destination=destination) #Sends user back to the form
        if endDate < startDate: #If the end date is before the start date
            flash('End date must be after start date')
            return render_template('new_holiday.html', destination=destination) #Sends user back to the form
        tempStartDate = datetime.strptime(startDate, '%Y-%m-%d')  #Takes start date and converts it to a datetime object
        tempEndDate = datetime.strptime(endDate, '%Y-%m-%d')    #"" with end date
        if (tempEndDate - tempStartDate).days > 90: #If the holiday is longer than 30 days
            flash('Holidays must be less than 90 days')
            return render_template('new_holiday.html', destination=destination) #Sends user back to the form
        if tempStartDate < datetime.today():
            flash('Start date must be today or in the future')
            return render_template('new_holiday.html', destination=destination)
        
        holidayConnection = sqlite3.connect('users.db')
        try:
            holidayCursor = holidayConnection.cursor()
            holidayCursor.execute("INSERT INTO holidays (countryName, startDate, endDate, userID, holidayTitle ) VALUES (?, ?, ?, ?, ?)",
                            (destination, startDate, endDate, userID, holiday_title)) #Inserts data into database
            holidayID = holidayCursor.lastrowid #Gets the primary key of the user's holiday
            holidayConnection.commit()
        finally:
            holidayConnection.close()   
        return redirect(url_for('calendar', holidayID = holidayID)) #Redirects user to the calendar page
    destination = request.args.get('destination') #Gets the destination from the URL if form not submitted
    if not destination: #If no destination is in the URL
        return redirect(url_for('dashboard')) #Redirects user to the dashboard
    return render_template('new_holiday.html', destination=destination) #If destination is in the URL, renders the new holiday page
 
@app.route('/calendar', methods=['GET', 'POST'])
def calendar():
    holidayID = request.args.get('holidayID', -1)  # Get the holiday ID from query parameters
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if holidayID == -1:
        return redirect(url_for('dashboard'))

    # Fetch holiday start and end dates
    dateConnection = sqlite3.connect('users.db')
    try:
        dateCursor = dateConnection.cursor()
        dateCursor.execute("SELECT startDate, endDate, cost FROM holidays WHERE holidayID = ?", (holidayID,))
        holiday_data = dateCursor.fetchone()
        dates = holiday_data[:2]  #Extracts the start and end dates
        total_cost = holiday_data[2]  #Extracts the cost of the holiday
    finally:
        dateConnection.close()

    start_date = datetime.strptime(dates[0], '%Y-%m-%d')  #Takes start date and converts it to a datetime object
    end_date = datetime.strptime(dates[1], '%Y-%m-%d')    #"" with end date

    #Generates a list of all dates for the holiday
    all_dates = []
    for i in range((end_date - start_date).days + 1):
        all_dates.append((start_date + timedelta(days=i)).strftime('%A, %Y-%m-%d'))

    conn = sqlite3.connect('users.db')
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT activityName FROM activities WHERE holidayID = ?", (holidayID,))
        activity_names_db = cursor.fetchall()  # Returns a tuple of all activities for the holiday
    finally:
        conn.close()

    activity_names = []
    for activity in activity_names_db:
        activity_names.append(activity[0]) #Converts tuple into a list of activity names

    conn = sqlite3.connect('users.db')
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT activityID, activityName, startTime, location, additionalNotes, price FROM activities WHERE holidayID = ?", (holidayID,))
        activities = cursor.fetchall()
    finally:
        conn.close() 

    activities_list = []
    for activity in activities:
            activities_list.append({
                'id': activity[0],  # rowid from the database
                'name': activity[1],
                'time': activity[2],
                'location': activity[3],
                'notes': activity[4],
                'cost' : activity[5]
            }) #Converts tuple into a list of dictionaries with activity details

    #Passes the full list of dates to the template
    return render_template(
        'calendar.html',
        holidayID=holidayID,
        all_dates=all_dates,  #Sends the list of all dates
        activity_names = activity_names, #Sends the list of activity names
        calendar_data = json.dumps(activities_list), #Sends the list of activities' details
        activities_list = activities_list, #Sends the list of activities' details
        total_cost = total_cost #Sends the total cost of the holiday
    )

@app.route('/new_activity', methods=['GET', 'POST'])
def new_activity(): #Defines the new_activity function
    if 'user_id' not in session: #Checks if the user is logged in
        return redirect(url_for('login'))
    if request.method == 'POST':
        user_id = session['user_id']
        holidayID = request.form.get('holidayID') #Gets the holiday ID from the hidden input field
        if not holidayID:
            return redirect(url_for('dashboard')) #If no holiday ID is found, user is redirected to the dashboard
        activity_name = request.form.get('activity_name')
        if len(activity_name) > 16:
            flash('Activity name must be 16 characters or less')
            return redirect(url_for('new_activity', holidayID=holidayID))
        activity_date = request.form.get('activity_date')
        activity_location = request.form.get('activity_location')
        booking_link = request.form.get('booking_link')
        additional_notes = request.form.get('additional_notes') #Gets all data to be stored in database
        activity_cost = request.form.get('activity_cost') or 0

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO activities (holidayID, userID, startTime, location, bookingLink, additionalNotes, activityName, price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (holidayID, user_id, activity_date, activity_location, booking_link, additional_notes, activity_name, activity_cost))
            #Inserts data into database
            cursor.execute("SELECT SUM(price) FROM activities WHERE holidayID = ?", (holidayID,)) #Gets the total cost of all activities
            total_cost = cursor.fetchone()[0] or 0 #Gives sum of all prices, or 0 if no activities
            cursor.execute("UPDATE holidays SET cost = ? WHERE holidayID = ?", (total_cost, holidayID)) #Updates the total cost of the holiday for relevant holiday 
            conn.commit()
        finally:
            conn.close()
        return redirect(url_for('calendar', holidayID=holidayID))
    holidayID = request.args.get('holidayID') #If form isn't filled in, holiday ID is taken from URL
    if holidayID:
        return render_template('new_activity.html', holidayID=holidayID)
    return redirect(url_for('dashboard'))

@app.route('/save_calendar', methods=['POST'])
def save_calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    holiday_id = request.form.get('holiday-id')
    holiday_title_list = request.form.getlist('holiday-title')
    if holiday_title_list: #Makes a list of holiday titles to add to the database
        holiday_title = holiday_title_list[0]
    else:
        holiday_title = ''
    calendar_data = json.loads(request.form.get('calendar-data')) #Gets calendar data from the form
    
    conn = sqlite3.connect('users.db')
    try:
        cursor = conn.cursor()
        if holiday_title: #Sets holiday title to new title
            cursor.execute("UPDATE holidays SET holidayTitle = ? WHERE holidayID = ?", 
                         (holiday_title, holiday_id))
        
        for activity in calendar_data: #Goes through each activity to add the start time to the database
            cursor.execute("UPDATE activities SET startTime = ? WHERE activityID = ?", 
                         (activity['startTime'], activity['activityId']))
        
        conn.commit()
    finally:
        conn.close()
    
    return redirect(url_for('calendar', holidayID=holiday_id)) #Opens calendar page back up

if __name__ == '__main__':
    app.run(debug=True)



