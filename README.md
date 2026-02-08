# Selwyn Dance School Web Application

## Authorship Statement
I used AI (DeepSeek) assistance for:
- Code structure suggestions
- Multiple complex functions
- Bootstrap layout examples
- SQL query debugging
- Form validation patterns

All code was reviewed, tested, and understood before implementation.

## Design Decisions
1. **Use of Image**: Only used one image for the Home page. When I did my google search I made sure the image is not copyrighted. 
2. **Teacher List Page**: Reworked on the teacher_list.html file to make sure the page sytle is consistent with other pages such as student list.
3. **Teacher Details**: I added Email, Phone and Status details (In /Teachers Route) for teachers and presented those information in teacher list so they are more contacatble by parents and students.
4. **Search Integration**: Added Student search to existing student list page - no extra html needed. The search was implemented with SQL queries that use 'LIKE' matching pattern on both first_name and last_name of students.
5. **Basic Validation**: The already enrolled classes should not be visable for the students when they want to select new classes to enrol
6. **Separate Template for Edit/Add** In our previpus lecture, we used the same form for add and edit teams. In this assignment I chose to separate the forms into add_student and edit_student as I found that this is easier for code maintainenance, and it also makes the logics clearer for future review.
7. **Assumption on enrolment**: I made an assumption that any newly added students can enrol with classes where class grade level <= 1. Already enrolled student can only choose the same type of classes they are at with grade + 1.

## Image Source
Home page image from Goole Search - not copyrighted