import pandas as pd
import streamlit as st
from dataclasses import dataclass
from typing import List, Dict, Set
import random
import matplotlib.pyplot as plt
import textwrap
from collections import defaultdict
import math

# Constants for days and times
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
TIME_SLOTS = [
    '08:45-09:45', '09:45-10:45', '10:45-11:45', '11:00-12:00', '12:00-13:00',
    '14:15-15:15', '15:15-16:15', '16:30-17:30'
]
MORNING_SLOTS = TIME_SLOTS[:4]
AFTERNOON_SLOTS = TIME_SLOTS[4:]
COLORS = [
    "#FF9999", "#99FF99", "#9999FF", "#FFFF99", "#FF99FF",
    "#99FFFF", "#FFB366", "#99CC99", "#9999CC", "#FFCC99",
    "#FF99CC", "#99FFCC", "#CC99FF", "#FFFF66", "#FF66FF"
]

@dataclass(frozen=True)
class Course:
    code: str
    name: str
    credits: int
    semester: int
    branch: str
    color: str = None

@dataclass
class CourseAssignment:
    course: Course
    faculty: str

@dataclass
class Section:
    name: str
    semester: int
    branch: str
    student_count: int
    course_assignments: List[CourseAssignment]

@dataclass
class Room:
    number: str
    capacity: int

@dataclass
class TimeTableSlot:
    day: str
    time: str
    course: Course
    room: Room
    section: Section
    faculty: str

class TimeTableGenerator:
    def __init__(self, courses_df, faculty_df, rooms_df, semester_type: str, student_counts: Dict[str, Dict[int, int]]):
        self.courses_df = courses_df
        self.faculty_df = faculty_df
        self.rooms_df = rooms_df
        self.semester_type = semester_type.lower()
        self.student_counts = student_counts
        self.rooms: List[Room] = []
        self.sections: Dict[str, Dict[int, List[Section]]] = {}
        self.timetable: Dict[str, List[TimeTableSlot]] = {}
        self.faculty_schedule: Dict[str, Dict[str, Set[str]]] = {}
        self.section_schedule: Dict[str, Dict[str, Set[str]]] = {}
        self.room_schedule: Dict[str, Dict[str, Set[str]]] = {}
        self.daily_course_count: Dict[str, Dict[str, int]] = {}

        self._initialize_data()

    def _need_multiple_sections(self, student_count: int) -> bool:
        max_room_capacity = max(room.capacity for room in self.rooms)
        return student_count > max_room_capacity

    def _create_course_assignments(self, courses_data: pd.DataFrame, branch: str, semester: int) -> List[CourseAssignment]:
     course_assignments = []
     faculty_assignments = {}  # Dictionary to track assigned faculty for each course

     for _, row in courses_data.iterrows():
        if int(row['Semester']) == semester and row['Branch'].lower() == branch:
            course = Course(
                code=row['Course Code'],
                name=row['Course Name'],
                credits=int(row['Credits']),
                semester=semester,
                branch=branch,
                color=COLORS[len(course_assignments) % len(COLORS)]
            )

            # Randomly select one faculty member for the course (assigned once per semester)
            if course.code not in faculty_assignments:
                faculty_list = [f.strip() for f in str(row['Faculty Members']).split(',')]
                selected_faculty = random.choice(faculty_list)
                faculty_assignments[course.code] = selected_faculty  # Assign the faculty for the course
            
            # Assign the selected faculty to all the credits of the course
            for _ in range(course.credits):
                course_assignments.append(CourseAssignment(
                    course=course,
                    faculty=faculty_assignments[course.code]
                ))

     return course_assignments

  

    def _initialize_data(self):
        #Initialize rooms
        for _, row in self.rooms_df.iterrows():
            self.rooms.append(Room(row['Room Number'], row['Capacity']))
            self.room_schedule[row['Room Number']] = {day: set() for day in DAYS}

        # Determine target semesters based on semester type
        target_semesters = [2, 4, 6, 8] if self.semester_type == 'even' else [1, 3, 5, 7]
        target_branches = ['cse', 'ece', 'aids']
        
        # Initialize sections dictionary
        self.sections = {branch: {sem: [] for sem in target_semesters} for branch in target_branches}

        # Process each branch and semester
        for branch in target_branches:
            for semester in target_semesters:
                year = (semester + 1) // 2
                student_count = self.student_counts[branch][year]

                # Check if multiple sections are needed
                need_multiple = self._need_multiple_sections(student_count)
            
                if need_multiple:
                    min_room_capacity = min(room.capacity for room in self.rooms)
                    num_sections = math.ceil(student_count / min_room_capacity)
                    students_per_section = math.ceil(student_count / num_sections)
                else:
                    num_sections = 1
                    students_per_section = student_count

                # Create sections with course assignments
                for section_num in range(num_sections):
                    section_name = f"S{semester}{branch.upper()}{chr(65 + section_num)}"
                    course_assignments = self._create_course_assignments(
                    self.courses_df, branch, semester
                    )
                    section = Section(
                        name=section_name,
                        semester=semester,
                        branch=branch,
                        student_count=students_per_section,
                        course_assignments=course_assignments
                    )
                    self.sections[branch][semester].append(section)
                    self.daily_course_count[section_name] = {day: 0 for day in DAYS}
                    self.section_schedule[section_name] = {day: set() for day in DAYS}

                    
        # Add new subjects to the existing sections
        for _, row in self.courses_df.iterrows():
            semester = row['Semester']
            branch = row['Branch'].lower()
            if semester in target_semesters and branch in target_branches:
                course = Course(
                code=row['Course Code'],
                name=row['Course Name'],
                credits=row['Credits'],
                semester=semester,
                branch=branch,
                color=COLORS[len(self.sections[branch][semester]) % len(COLORS)]
                )
            
                faculty_list = [f.strip() for f in str(row['Faculty Members']).split(',')]
                for _ in range(course.credits):
                    self.sections[branch][semester][0].course_assignments.append(CourseAssignment(
                        course=course,
                        faculty=random.choice(faculty_list)
                    ))

    def _is_slot_available(self, faculty: str, section: str, room: str, day: str, time: str) -> bool:
        if (faculty in self.faculty_schedule and time in self.faculty_schedule[faculty][day]):
            return False
        if time in self.section_schedule[section][day]:
            return False
        if time in self.room_schedule[room][day]:
            return False

        max_courses_per_day = 4
        if self.daily_course_count[section][day] >= max_courses_per_day:
            return False

        is_morning = time in MORNING_SLOTS
        morning_count = sum(1 for t in self.section_schedule[section][day] if t in MORNING_SLOTS)
        afternoon_count = sum(1 for t in self.section_schedule[section][day] if t in AFTERNOON_SLOTS)

        if is_morning and morning_count >= 3:
            return False
        if not is_morning and afternoon_count >= 2:
            return False

        return True

    def _mark_slot_used(self, faculty: str, section: str, room: str, day: str, time: str):
        if faculty in self.faculty_schedule:
            self.faculty_schedule[faculty][day].add(time)
        self.section_schedule[section][day].add(time)
        self.room_schedule[room][day].add(time)
        self.daily_course_count[section][day] += 1

    def _get_preferred_slots(self, current_day_count: int) -> List[str]:
        if current_day_count < 2:
            return MORNING_SLOTS + AFTERNOON_SLOTS
        elif current_day_count < 3:
            return AFTERNOON_SLOTS + MORNING_SLOTS
        else:
            return MORNING_SLOTS[-2:] + AFTERNOON_SLOTS

    def generate_timetable(self):
        all_sections = []
        for branch in self.sections:
            for semester in sorted(self.sections[branch].keys()):
                all_sections.extend(self.sections[branch][semester])

        max_attempts = 100

        for section in all_sections:
            print(f"Generating timetable for section {section.name} ({section.student_count} students)")
            self.timetable[section.name] = []

            # Calculate the required hours based on credits
            remaining_hours = defaultdict(int)
            for assignment in section.course_assignments:
                remaining_hours[assignment.course] += 1  # Each credit hour corresponds to one scheduled hour

            attempt = 0
            while any(hours > 0 for hours in remaining_hours.values()) and attempt < max_attempts:
                attempt += 1
                course_assignments = list(section.course_assignments)
                random.shuffle(course_assignments)

                for course_assignment in course_assignments:
                    course = course_assignment.course
                    if remaining_hours[course] <= 0:
                        continue

                    scheduled = False
                    # Sort days by load to distribute classes evenly
                    days_by_load = sorted(DAYS, key=lambda d: self.daily_course_count[section.name][d])

                    for day in days_by_load:
                        if scheduled:
                            break

                        current_day_count = self.daily_course_count[section.name][day]
                        preferred_slots = self._get_preferred_slots(current_day_count)

                        for time in preferred_slots:
                            available_rooms = [
                                r for r in self.rooms
                                if r.capacity >= section.student_count and
                                self._is_slot_available(course_assignment.faculty, section.name, r.number, day, time)
                            ]

                            if available_rooms:
                                room = min(available_rooms, key=lambda r: r.capacity)
                                slot = TimeTableSlot(
                                    day=day,
                                    time=time,
                                    course=course,
                                    room=room,
                                    section=section,
                                    faculty=course_assignment.faculty
                                )
                                self.timetable[section.name].append(slot)
                                self._mark_slot_used(course_assignment.faculty, section.name, room.number, day, time)
                                remaining_hours[course] -= 1
                                scheduled = True
                                break

            unscheduled = [
                f"{course.code}: {hours} hours"
                for course, hours in remaining_hours.items()
                if hours > 0
            ]
            if unscheduled:
                print(f"Warning: Could not schedule all hours for section {section.name}:")
                for item in unscheduled:
                    print(f"  {item}")

    # Visualization code adapted to work in Streamlit
    def visualize_timetable(self, section_name: str, save_as_image: bool = False):
        if section_name not in self.timetable:
            raise ValueError(f"No timetable found for section {section_name}")

        slots = self.timetable[section_name]
        section = next(
            section for branch in self.sections.values()
            for semester_sections in branch.values()
            for section in semester_sections
            if section.name == section_name
        )

        fig, ax = plt.subplots(figsize=(10, 6))

        for i, day in enumerate(DAYS):
            for j, time in enumerate(TIME_SLOTS):
                ax.plot([i, i+1], [j, j], 'k-', alpha=0.2)
                ax.plot([i, i], [j, j+1], 'k-', alpha=0.2)

                slot = next(
                    (s for s in slots if s.day == day and s.time == time),
                    None
                )

                if slot:
                    ax.fill_between(
                        [i, i+0.9],
                        [j, j],
                        [j+0.9, j+0.9],
                        color=slot.course.color,
                        alpha=0.6
                    )

                    text = f"{slot.course.code}\n{slot.course.name}\n{slot.faculty}\nRoom: {slot.room.number}"
                    wrapped_text = textwrap.fill(text, width=20)

                    ax.text(
                        i + 0.45,
                        j + 0.45,
                        wrapped_text,
                        ha='center',
                        va='center',
                        fontsize=8,
                        bbox=dict(facecolor='white', alpha=0.7)
                    )

        ax.grid(True, linestyle='--', alpha=0.3)
        ax.set_xticks(range(len(DAYS)))
        ax.set_xticklabels(DAYS, rotation=45)
        ax.set_yticks(range(len(TIME_SLOTS)))
        ax.set_yticklabels(TIME_SLOTS)
        ax.set_title(f"Timetable for Section {section_name} ({section.student_count} students)")

        # Save figure if save_as_image is True
        if save_as_image:
            fig.savefig(f"{section_name}_timetable.png", dpi=300)
            st.success(f"Timetable for {section_name} saved as {section_name}_timetable.png")

        st.pyplot(fig)

def check_subject_exists(courses_df, subject_code, subject_name):
    return (
        (courses_df['Course Code'].str.lower() == subject_code.lower()).any() or 
        (courses_df['Course Name'].str.lower() == subject_name.lower()).any()
    )

def check_faculty_exists(faculty_df, faculty_name):
    return (faculty_df['Faculty Name'].str.lower() == faculty_name.lower()).any()

def generate_faculty_id(faculty_df, branch):
    branch_prefix = branch.upper() + "-"
    existing_ids = faculty_df[faculty_df['Faculty ID'].str.startswith(branch_prefix)]['Faculty ID']
    if len(existing_ids) == 0:
        return f"{branch_prefix}101"
    max_num = max(int(id.split('-')[1]) for id in existing_ids)
    return f"{branch_prefix}{max_num + 1}"

def add_new_subject(courses_df, faculty_df):
    st.subheader("Add New Subject")
    
    subject_name = st.text_input("Subject Name")
    subject_code = st.text_input("Subject Code")
    branch = st.selectbox("Branch", ["CSE", "ECE", "AIDS"])
    semester = st.number_input("Semester", min_value=1, max_value=8)
    credits = st.number_input("Credits", min_value=1, max_value=4, value=4)
    
    num_faculty = st.number_input("Number of Faculty Teaching this Subject", min_value=1, max_value=10)
    
    faculty_list = []
    if subject_name and subject_code:
        st.subheader("Select Faculty Members")
        
        for i in range(int(num_faculty)):
            existing_faculty = st.selectbox(f"Faculty {i+1}", [""] + list(faculty_df['Faculty Name']), key=f"faculty_{i}")
            if existing_faculty:
                faculty_list.append(existing_faculty)
    
    if st.button("Add Subject"):
        if not (subject_name and subject_code):
            st.error("Please enter subject name and code")
            return courses_df
        
        if check_subject_exists(courses_df, subject_code, subject_name):
            st.error("Subject code or name already exists!")
            return courses_df
        
        if len(faculty_list) == 0:
            st.error("Please select at least one faculty member")
            return courses_df
        
        new_subject = pd.DataFrame({
            'Semester': [semester],
            'Course Code': [subject_code],
            'Course Name': [subject_name],
            'Faculty Members': [", ".join(faculty_list)],
            'Credits': [credits],
            'Branch': [branch]
        })
        
        courses_df = pd.concat([courses_df, new_subject], ignore_index=True)
        courses_df.to_csv("subjects.csv", index=False)
        st.success(f"Added subject {subject_name} ({subject_code})")
        
        return courses_df

def add_new_faculty(faculty_df):
    st.subheader("Add New Faculty")

    faculty_name = st.text_input("Faculty Name")
    faculty_id = st.text_input("Faculty ID")
    branch = st.selectbox("Branch", ["CSE", "ECE", "AIDS"])

    if st.button("Add Faculty"):
        if not faculty_name or not faculty_id:
            st.error("Please enter both faculty name and faculty ID.")
            return faculty_df

        # Check if faculty name or ID already exists
        if check_faculty_exists(faculty_df, faculty_name):
            st.error("Faculty name already exists! Please use a different name.")
            return faculty_df
        elif faculty_id in faculty_df['Faculty ID'].values:
            st.error("Faculty ID already exists! Please enter a unique ID.")
            return faculty_df

        # Add the new faculty member to the DataFrame
        new_faculty = pd.DataFrame({
            'Faculty Name': [faculty_name],
            'Faculty ID': [faculty_id],
            'Branch': [branch]
        })
        
        # Update the faculty DataFrame and save to CSV
        faculty_df = pd.concat([faculty_df, new_faculty], ignore_index=True)
        faculty_df.to_csv("faculty.csv", index=False)
        st.success(f"Added faculty member {faculty_name} with ID {faculty_id}")
        
        return faculty_df

def check_faculty_exists(faculty_df, faculty_name):
    # Check if a faculty name already exists in the DataFrame
    return faculty_name in faculty_df['Faculty Name'].values

def main():
    st.title("Institute Level Timetable Generator")

    # Step 1: Upload CSV files
    courses_file = st.file_uploader("Upload CSV for subjects:", type="csv")
    faculty_file = st.file_uploader("Upload CSV for faculty:", type="csv")
    rooms_file = st.file_uploader("Upload CSV for room and capacity:", type="csv")

    if courses_file and faculty_file and rooms_file:
        # Read CSVs
        courses_df = pd.read_csv(courses_file)
        faculty_df = pd.read_csv(faculty_file)
        rooms_df = pd.read_csv(rooms_file)

        # Select operation: Add New Subject, Add New Faculty, or Generate Timetable
        operation = st.selectbox("Select Operation", ["Add New Subject", "Add New Faculty", "Generate Timetable"])

        if operation == "Add New Subject":
            courses_df = add_new_subject(courses_df, faculty_df)

        elif operation == "Add New Faculty":
            faculty_df = add_new_faculty(faculty_df)

        elif operation == "Generate Timetable":
            st.header("Generate Timetable")
    
            # Input semester type and student counts
            semester_type = st.selectbox("Select Semester Type", ["Even", "Odd"]).lower()
            student_counts = {
                'cse': {},
                'ece': {},
                'aids': {}
            }

            for year in range(1, 5):
                st.write(f"Enter student counts for Year {year}:")
                total = st.number_input(f"Total number of students in Year {year}", min_value=0)
                cse = st.number_input(f"Number of students in CSE Year {year}", min_value=0, max_value=total)
                ece = st.number_input(f"Number of students in ECE Year {year}", min_value=0, max_value=(total - cse))
                aids = max(0, total - (cse + ece))

                st.write(f"AIDS students in Year {year}: {aids}")

                student_counts['cse'][year] = cse
                student_counts['ece'][year] = ece
                student_counts['aids'][year] = aids
            save_images = st.checkbox("Save Timetables as Images")

            if st.button("Generate Timetable"):
                generator = TimeTableGenerator(courses_df, faculty_df, rooms_df, semester_type, student_counts)
                generator.generate_timetable()
                
                for branch in generator.sections:
                    for semester in generator.sections[branch]:
                        for section in generator.sections[branch][semester]:
                            st.write(f"Timetable for {section.name}")
                            generator.visualize_timetable(section.name, save_as_image=save_images)

if __name__ == "__main__":
    main()