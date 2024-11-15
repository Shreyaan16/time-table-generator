import pandas as pd
import streamlit as st
from dataclasses import dataclass
from typing import List, Dict, Set
import random
import matplotlib.pyplot as plt
import textwrap
from collections import defaultdict
import math

# [Previous constants and classes remain the same until the TimeTableGenerator class]
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
        self.faculty_schedule: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: {day: set() for day in DAYS})
        self.section_schedule: Dict[str, Dict[str, Set[str]]] = {}
        self.room_schedule: Dict[str, Dict[str, Set[str]]] = {}
        self.daily_course_count: Dict[str, Dict[str, int]] = {}

        self._initialize_data()

    def _create_course_assignments(self, courses_data: pd.DataFrame, branch: str, semester: int) -> List[CourseAssignment]:
        course_assignments = []
        faculty_assignments = {}  # Track faculty assignments per course

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

                if course.code not in faculty_assignments:
                    faculty_list = [f.strip() for f in str(row['Faculty Members']).split(',')]
                    selected_faculty = random.choice(faculty_list)
                    faculty_assignments[course.code] = selected_faculty

                for _ in range(course.credits):
                    course_assignments.append(CourseAssignment(
                        course=course,
                        faculty=faculty_assignments[course.code]
                    ))

        return course_assignments

    def _initialize_data(self):
        # Initialize rooms
        for _, row in self.rooms_df.iterrows():
            self.rooms.append(Room(row['Room Number'], row['Capacity']))
            self.room_schedule[row['Room Number']] = {day: set() for day in DAYS}

        target_semesters = [2, 4, 6, 8] if self.semester_type == 'even' else [1, 3, 5, 7]
        target_branches = ['cse', 'ece', 'aids']
        
        self.sections = {branch: {sem: [] for sem in target_semesters} for branch in target_branches}

        for branch in target_branches:
            for semester in target_semesters:
                year = (semester + 1) // 2
                student_count = self.student_counts[branch][year]
                
                need_multiple = student_count > max(room.capacity for room in self.rooms)
                
                if need_multiple:
                    min_room_capacity = min(room.capacity for room in self.rooms)
                    num_sections = math.ceil(student_count / min_room_capacity)
                    students_per_section = math.ceil(student_count / num_sections)
                else:
                    num_sections = 1
                    students_per_section = student_count

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

    def _is_slot_available(self, faculty: str, section: str, room: str, day: str, time: str) -> bool:
        if time in self.faculty_schedule[faculty][day]:
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

    # Previous code remains the same until the generate_timetable method
    def _attempt_schedule_courses(self, section: Section, remaining_hours: Dict[Course, int],
                                course_room_history: Dict[str, Set[str]]):
        """Attempt to schedule courses for a section."""
        course_assignments = list(section.course_assignments)
        random.shuffle(course_assignments)

        for assignment in course_assignments:
            if remaining_hours[assignment.course] <= 0:
                continue

            days_by_load = sorted(DAYS, 
                                key=lambda d: self.daily_course_count[section.name][d])

            for day in days_by_load:
                if self._try_schedule_course(section, assignment, day, 
                                          course_room_history):
                    remaining_hours[assignment.course] -= 1
                    break
    
    def _try_schedule_course(self, section: Section, assignment: CourseAssignment,
                           day: str, course_room_history: Dict[str, Set[str]]) -> bool:
        """Try to schedule a single course session."""
        current_day_count = self.daily_course_count[section.name][day]
        preferred_slots = (MORNING_SLOTS + AFTERNOON_SLOTS if current_day_count < 2 
                         else AFTERNOON_SLOTS + MORNING_SLOTS)

        for time in preferred_slots:
            suitable_rooms = [
                room for room in self.rooms
                if (room.capacity >= section.student_count and
                    self._is_slot_available(assignment.faculty, section.name, 
                                         room.number, day, time))
            ]

            if not suitable_rooms:
                continue

            room = self._select_best_room(suitable_rooms, assignment.course.code,
                                        course_room_history, section.name)
            
            self._schedule_slot(section, assignment, day, time, room)
            self._update_room_history(course_room_history, assignment.course.code,
                                    room.number)
            return True

        return False

    def _select_best_room(self, suitable_rooms: List[Room], course_code: str,
                         course_room_history: Dict[str, Set[str]], 
                         section_name: str) -> Room:
        """Select the best room for a course session."""
        unused_rooms = [
            room for room in suitable_rooms
            if room.number not in course_room_history[course_code]
        ]

        if unused_rooms:
            return min(unused_rooms, key=lambda r: r.capacity)
        
        return min(
            suitable_rooms,
            key=lambda r: (
                len([s for s in self.timetable[section_name] 
                     if s.room.number == r.number and 
                     s.course.code == course_code]),
                r.capacity
            )
        )

    def _schedule_slot(self, section: Section, assignment: CourseAssignment,
                      day: str, time: str, room: Room):
        """Schedule a single time slot."""
        slot = TimeTableSlot(
            day=day,
            time=time,
            course=assignment.course,
            room=room,
            section=section,
            faculty=assignment.faculty
        )

        self.timetable[section.name].append(slot)
        self.faculty_schedule[assignment.faculty][day].add(time)
        self.section_schedule[section.name][day].add(time)
        self.room_schedule[room.number][day].add(time)
        self.daily_course_count[section.name][day] += 1

    def _update_room_history(self, course_room_history: Dict[str, Set[str]],
                           course_code: str, room_number: str):
        """Update the course-room usage history."""
        course_room_history[course_code].add(room_number)
        if len(course_room_history[course_code]) > 3:
            course_room_history[course_code].pop()

    def _validate_timetable(self) -> List[str]:
        """Validate the generated timetable for common issues."""
        issues = []
        
        for section_name, slots in self.timetable.items():
            course_rooms = defaultdict(set)
            for slot in slots:
                course_rooms[slot.course.code].add(slot.room.number)
                
            self._check_room_variety(section_name, course_rooms, slots, issues)
            self._check_distribution(section_name, slots, issues)
        
        return issues

    def _check_room_variety(self, section_name: str, course_rooms: Dict[str, Set[str]],
                          slots: List[TimeTableSlot], issues: List[str]):
        """Check for adequate variety in room assignments."""
        for course_code, rooms in course_rooms.items():
            if len(rooms) == 1 and len([s for s in slots 
                                      if s.course.code == course_code]) > 2:
                issues.append(
                    f"Warning: Course {course_code} in section {section_name} "
                    "uses same room for all sessions"
                )

    def _check_distribution(self, section_name: str, slots: List[TimeTableSlot],
                          issues: List[str]):
        """Check for balanced distribution of classes across days."""
        day_counts = defaultdict(int)
        for slot in slots:
            day_counts[slot.day] += 1
            
        max_count = max(day_counts.values())
        min_count = min(day_counts.values())
        if max_count - min_count > 2:
            issues.append(
                f"Warning: Uneven distribution of classes across days in section "
                f"{section_name}"
            )

    def _generate_statistics(self) -> Dict:
        """Generate statistics about the timetable and resource utilization.
        
        Returns:
            Dict containing statistics about total slots scheduled, room utilization,
            faculty workload, time slot usage, and other metrics.
        """
        stats = {
            'total_slots_scheduled': 0,
            'room_utilization': defaultdict(int),
            'faculty_load': defaultdict(int),
            'time_slot_usage': defaultdict(int),
            'course_distribution': defaultdict(lambda: defaultdict(int)),
            'section_metrics': defaultdict(lambda: {
                'total_slots': 0,
                'unique_rooms': set(),
                'morning_slots': 0,
                'afternoon_slots': 0
            }),
            'daily_distribution': defaultdict(lambda: defaultdict(int))
        }
        
        # Process each section's timetable
        for section_name, slots in self.timetable.items():
            for slot in slots:
                # Increment total slots
                stats['total_slots_scheduled'] += 1
                
                # Room utilization
                stats['room_utilization'][slot.room.number] += 1
                
                # Faculty workload
                stats['faculty_load'][slot.faculty] += 1
                
                # Time slot usage
                stats['time_slot_usage'][slot.time] += 1
                
                # Course distribution per section
                stats['course_distribution'][section_name][slot.course.code] += 1
                
                # Section-specific metrics
                section_stats = stats['section_metrics'][section_name]
                section_stats['total_slots'] += 1
                section_stats['unique_rooms'].add(slot.room.number)
                
                if slot.time in MORNING_SLOTS:
                    section_stats['morning_slots'] += 1
                else:
                    section_stats['afternoon_slots'] += 1
                
                # Daily distribution
                stats['daily_distribution'][section_name][slot.day] += 1
        
        # Calculate additional metrics
        stats['avg_slots_per_section'] = (stats['total_slots_scheduled'] / 
                                        len(self.timetable) if self.timetable else 0)
        
        # Convert room sets to counts in section metrics
        for section_name in stats['section_metrics']:
            stats['section_metrics'][section_name]['unique_rooms'] = (
                len(stats['section_metrics'][section_name]['unique_rooms'])
            )
        
        # Calculate room utilization percentages
        total_possible_slots = len(DAYS) * len(TIME_SLOTS)
        stats['room_utilization_percentage'] = {
            room: (count / total_possible_slots) * 100
            for room, count in stats['room_utilization'].items()
        }
        
        # Calculate faculty utilization percentages
        stats['faculty_utilization_percentage'] = {
            faculty: (count / total_possible_slots) * 100
            for faculty, count in stats['faculty_load'].items()
        }
        
        # Calculate time slot popularity
        total_slot_usage = sum(stats['time_slot_usage'].values())
        if total_slot_usage > 0:
            stats['time_slot_popularity'] = {
                time: (count / total_slot_usage) * 100
                for time, count in stats['time_slot_usage'].items()
            }
        
        return stats
    def generate_timetable(self):
        """Generate the complete timetable for all sections."""
        all_sections = [
            section for branch_sections in self.sections.values()
            for semester_sections in branch_sections.values()
            for section in semester_sections
        ]

        if not all_sections:
            st.error("No sections found to generate timetable. Please check your input data.")
            return None

        generation_success = True
        for section in all_sections:
            success = self._generate_section_timetable(section)
            if not success:
                st.error(f"Failed to generate complete timetable for section {section.name}")
                generation_success = False

        if generation_success:
            validation_issues = self._validate_timetable()
            if validation_issues:
                for issue in validation_issues:
                    st.warning(issue)
            return self._generate_statistics()
        return None

    def _generate_section_timetable(self, section: Section) -> bool:
        """
        Generate timetable for a specific section.
        Returns True if successful, False otherwise.
        """
        self.timetable[section.name] = []
        remaining_hours = defaultdict(int)
        course_room_history = defaultdict(set)

        for assignment in section.course_assignments:
            remaining_hours[assignment.course] += 1

        if not remaining_hours:
            st.error(f"No courses found for section {section.name}")
            return False

        attempts = 0
        max_attempts = 100

        while any(hours > 0 for hours in remaining_hours.values()) and attempts < max_attempts:
            attempts += 1
            self._attempt_schedule_courses(section, remaining_hours, course_room_history)

        if any(hours > 0 for hours in remaining_hours.values()):
            st.error(f"Could not schedule all courses for section {section.name} after {max_attempts} attempts")
            unscheduled = [f"{course.code}: {hours} hours" 
                        for course, hours in remaining_hours.items() if hours > 0]
            st.error(f"Unscheduled courses: {', '.join(unscheduled)}")
            return False

        return True

    def _validate_timetable(self) -> List[str]:
        """Validate the generated timetable for common issues."""
        issues = []
        
        for section_name, slots in self.timetable.items():
            if not slots:
                issues.append(f"No slots scheduled for section {section_name}")
                continue

            course_rooms = defaultdict(set)
            day_counts = defaultdict(int)
            
            for slot in slots:
                course_rooms[slot.course.code].add(slot.room.number)
                day_counts[slot.day] += 1

            # Validate room variety
            for course_code, rooms in course_rooms.items():
                course_slots = [s for s in slots if s.course.code == course_code]
                if len(rooms) == 1 and len(course_slots) > 2:
                    issues.append(
                        f"Warning: Course {course_code} in section {section_name} "
                        f"uses same room ({next(iter(rooms))}) for all {len(course_slots)} sessions"
                    )

            # Validate distribution across days
            if day_counts:  # Only check if there are scheduled slots
                max_count = max(day_counts.values())
                min_count = min(day_counts.values())
                if max_count - min_count > 2:
                    counts_str = ", ".join(f"{day}: {count}" for day, count in day_counts.items())
                    issues.append(
                        f"Warning: Uneven distribution of classes across days in section "
                        f"{section_name} ({counts_str})"
                    )

        return issues

    def visualize_timetable(self, section_name: str, save_as_image: bool = False):
        """Visualize the timetable for a specific section."""
        if section_name not in self.timetable:
            st.error(f"No timetable found for section {section_name}")
            return

        slots = self.timetable[section_name]
        if not slots:
            st.error(f"No classes scheduled for section {section_name}")
            return

        section = next(
            (section for branch in self.sections.values()
            for semester_sections in branch.values()
            for section in semester_sections
            if section.name == section_name),
            None
        )

        if not section:
            st.error(f"Section {section_name} not found in data")
            return

        fig, ax = plt.subplots(figsize=(15, 8))

        # Create the base grid
        for i, day in enumerate(DAYS):
            for j, time in enumerate(TIME_SLOTS):
                ax.plot([i, i+1], [j, j], 'k-', alpha=0.2)
                ax.plot([i, i], [j, j+1], 'k-', alpha=0.2)

                slot = next(
                    (s for s in slots if s.day == day and s.time == time),
                    None
                )

                if slot:
                    # Fill the cell with course information
                    ax.fill_between(
                        [i, i+0.9],
                        [j, j],
                        [j+0.9, j+0.9],
                        color=slot.course.color,
                        alpha=0.6
                    )

                    text = (f"{slot.course.code}\n{slot.course.name}\n"
                        f"{slot.faculty}\nRoom: {slot.room.number}")
                    wrapped_text = textwrap.fill(text, width=25)

                    ax.text(
                        i + 0.45,
                        j + 0.45,
                        wrapped_text,
                        ha='center',
                        va='center',
                        fontsize=8,
                        bbox=dict(facecolor='white', alpha=0.7)
                    )

        # Customize the plot
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.set_xticks(range(len(DAYS)))
        ax.set_xticklabels(DAYS, rotation=45)
        ax.set_yticks(range(len(TIME_SLOTS)))
        ax.set_yticklabels(TIME_SLOTS)
        ax.set_title(f"Timetable for Section {section_name} ({section.student_count} students)")

        plt.tight_layout()

        if save_as_image:
            try:
                fig.savefig(f"{section_name}_timetable.png", dpi=300, bbox_inches='tight')
                st.success(f"Timetable saved as {section_name}_timetable.png")
            except Exception as e:
                st.error(f"Failed to save timetable image: {str(e)}")

        st.pyplot(fig)

def check_subject_exists(courses_df, subject_code, subject_name):
    return (
        (courses_df['Course Code'].str.lower() == subject_code.lower()).any() or 
        (courses_df['Course Name'].str.lower() == subject_name.lower()).any()
    )

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

def append_faculty_to_subject(courses_df: pd.DataFrame):
    st.subheader("Append Faculty to Existing Subject")
    
    # Get unique branches
    branches = sorted(courses_df['Branch'].unique())
    selected_branch = st.selectbox("Select Branch", branches)
    
    # Get subjects for selected branch
    branch_subjects = courses_df[courses_df['Branch'] == selected_branch]
    subject_codes = sorted(branch_subjects['Course Code'].unique())
    selected_subject = st.selectbox("Select Subject", subject_codes)
    
    # Display current subject details
    subject_row = courses_df[
        (courses_df['Course Code'] == selected_subject) & 
        (courses_df['Branch'] == selected_branch)
    ].iloc[0]
    
    st.write("Current Subject Details:")
    st.write(f"Name: {subject_row['Course Name']}")
    st.write(f"Current Faculty: {subject_row['Faculty Members']}")
    
    # Input for new faculty
    new_faculty = st.text_input("Enter New Faculty Name")
    
    if st.button("Append Faculty"):
        if not new_faculty:
            st.error("Please enter faculty name")
            return courses_df
            
        # Update faculty members for the selected subject
        mask = (courses_df['Course Code'] == selected_subject) & (courses_df['Branch'] == selected_branch)
        current_faculty = courses_df.loc[mask, 'Faculty Members'].iloc[0]
        
        if pd.isna(current_faculty):
            updated_faculty = new_faculty
        else:
            # Check if faculty already exists
            current_faculty_list = [f.strip() for f in current_faculty.split(',')]
            if new_faculty in current_faculty_list:
                st.error("Faculty already assigned to this subject!")
                return courses_df
            updated_faculty = f"{current_faculty}, {new_faculty}"
        
        courses_df.loc[mask, 'Faculty Members'] = updated_faculty
        
        # Save updated DataFrame
        courses_df.to_csv("subjects.csv", index=False)
        st.success(f"Successfully added {new_faculty} to {selected_subject}")
    
    return courses_df

def add_new_faculty(faculty_df: pd.DataFrame, courses_df: pd.DataFrame):
    st.subheader("Add New Faculty")

    faculty_name = st.text_input("Faculty Name")
    faculty_id = st.text_input("Faculty ID")
    branch = st.selectbox("Branch", ["CSE", "ECE", "AIDS"])

    if st.button("Add Faculty"):
        if not faculty_name or not faculty_id:
            st.error("Please enter both faculty name and faculty ID.")
            return faculty_df, courses_df

        if faculty_name in faculty_df['Faculty Name'].values:
            st.error("Faculty name already exists!")
            return faculty_df, courses_df
        if faculty_id in faculty_df['Faculty ID'].values:
            st.error("Faculty ID already exists!")
            return faculty_df, courses_df

        new_faculty = pd.DataFrame({
            'Faculty Name': [faculty_name],
            'Faculty ID': [faculty_id],
            'Branch': [branch]
        })
        
        updated_faculty_df = pd.concat([faculty_df, new_faculty], ignore_index=True)
        updated_faculty_df.to_csv("faculty.csv", index=False)
        st.success(f"Added faculty member {faculty_name} with ID {faculty_id}")
        
        return updated_faculty_df, courses_df
    
    return faculty_df, courses_df

def main():
    st.title("Institute Level Timetable Generator")

    courses_file = st.file_uploader("Upload CSV for subjects:", type="csv")
    
    faculty_file = st.file_uploader("Upload CSV for faculty:", type="csv")
    rooms_file = st.file_uploader("Upload CSV for room and capacity:", type="csv")

    if courses_file and faculty_file and rooms_file:
        courses_df = pd.read_csv(courses_file)
        faculty_df = pd.read_csv(faculty_file)
        rooms_df = pd.read_csv(rooms_file)

        st.write("The columns of the dataframe are: ")

        st.write('\nSubjects-csv')
        st.dataframe(courses_df)

        st.write('\nFaculty-csv')
        st.dataframe(faculty_df)


        st.write('\nRooms-csv')
        st.dataframe(rooms_df)

        operation = st.selectbox(
            "Select Operation", 
            ["Add New Faculty","Add New Subject", "Append Faculty to Subject", "Generate Timetable"]
        )

        if operation == "Add New Faculty":
            faculty_df, courses_df = add_new_faculty(faculty_df, courses_df)
        
        elif operation == "Add New Subject":
            courses_df = add_new_subject(courses_df, faculty_df)
            
        elif operation == "Append Faculty to Subject":
            courses_df = append_faculty_to_subject(courses_df)

        elif operation == "Generate Timetable":
            st.header("Generate Timetable")
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
    footer_html = """<div style='text-align: center; font-family: Arial, sans-serif; color: #999; padding-top: 20px;'>
        <p style='font-size: 14px; margin: 0;'>Made with ❤ during the DataZen Hackathon</p>
        <p style='font-size: 16px; margin: 5px 0;'>By Team Outliers</p>
        <p style='font-size: 14px; margin: 0;'>Including Purval Bhude, Shreyaan Loke, and Dhruv Patel</p>
        </div>"""
    st.markdown(footer_html, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
