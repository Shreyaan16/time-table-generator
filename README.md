#Timetable Generator 📅
Overview:
This Timetable Generator provides an efficient and flexible solution for scheduling classes, ensuring:
No scheduling conflicts between classes.
No conflicts in teacher allocation, ensuring no teacher is assigned to multiple classes simultaneously.
Inclusion of free slots to accommodate extra classes or unforeseen schedule adjustments.
Flexibility to add new subjects, assign new faculty to existing subjects, and proportionally allocate classes based on subject credits.
The project uses pure Python, basic data science techniques, and is deployed on Streamlit for ease of use.

Features
Conflict-free scheduling for multiple semesters, branches, and courses.
Faculty flexibility: Assign new faculty members to teach existing subjects.
Proportional allocation of classes: Classes in a week are scheduled proportionally to the subject's credit value.
Room assignment: Rooms are allocated based on class size and availability.
Free slots: Includes dedicated free slots for remedial or extra classes.
Timetable export: Save the generated timetable as an image for easy sharing.
Integrated chatbot: A generic chatbot is included (not fine-tuned yet) to assist with queries.
Streamlit deployment: User-friendly web interface for seamless interaction and functionality.
Input Requirements
The program requires three input CSV files:

1. subjects.csv
Contains details of the courses being offered.

Column	Description:
Semester	Semester for which the course is offered.
Course Code	Unique code for the course.
Course Name	Name of the course.
Faculty Members	Faculty members teaching the course.
Credits	Number of credits for the course.
Branch	Branch to which the course belongs.

2. rooms.csv
Contains details of the rooms available for classes.

Column	Description:
Room Number	Unique identifier for the room.
Capacity	Maximum capacity of the room.

3. faculty.csv
Contains details of the faculty members.

Column	Description:
Faculty ID	Unique identifier for the faculty member.
Faculty Name	Name of the faculty member.
Branch	Branch/department the faculty belongs to.

How It Works:
The program reads the input CSV files and validates the data for any inconsistencies.
It dynamically adjusts schedules based on:
Credits of the course to determine weekly class frequency.
Room availability and size constraints.
Faculty schedules to avoid conflicts.
New subjects or faculty members can be added seamlessly.
The generated timetable is displayed in the Streamlit interface, with an option to save it as an image.
Deployment
The application is deployed on Streamlit, providing an intuitive user interface.

Also hosted on streamlit 
link : 
time-table-generator.streamlit.app

Acknowledgments:
A big thank you to my teammates Purval Bhude and Dhruv Patel for their contributions and collaboration on this project.
