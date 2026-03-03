def to_class_sessions(api_response: dict, term: str = "") -> list:
    sessions = []
    schools = (api_response or {}).get("schools") or []

    def _str(x):
        if x is None:
            return ""
        if isinstance(x, list):
            return " ".join(_str(i) for i in x)
        return str(x).strip()

    for school in schools:
        for dept in school.get("departments") or []:
            for course in dept.get("courses") or []:
                dept_code = _str(dept.get("deptCode"))
                course_num = _str(course.get("courseNumber"))
                course_id = f"{dept_code} {course_num}".strip()
                course_title = _str(course.get("courseTitle"))

                for section in course.get("sections") or []:
                    instructors = section.get("instructors") or []
                    instructor_name = ", ".join(_str(x) for x in instructors if x) or None
                    meetings = section.get("meetings") or []

                    enrolled = section.get("numCurrentlyEnrolled") or {}
                    if isinstance(enrolled, dict):
                        num_enrolled = enrolled.get("sectionEnrolled") or enrolled.get("totalEnrolled")
                    else:
                        num_enrolled = None
                    num_enrolled = _str(num_enrolled) if num_enrolled is not None else None

                    base = {
                        "courseCode": course_id,
                        "courseTitle": course_title,
                        "sectionCode": _str(section.get("sectionCode")),
                        "sectionType": _str(section.get("sectionType")),
                        "sectionNum": _str(section.get("sectionNum")),
                        "instructorName": instructor_name,
                        "term": term,
                        "units": _str(section.get("units")),
                        "status": _str(section.get("status")),
                        "maxCapacity": _str(section.get("maxCapacity")),
                        "numEnrolled": num_enrolled,
                    }

                    if not meetings:
                        sessions.append({
                            **base,
                            "meetingTime": None,
                            "days": "TBA",
                            "location": None,
                        })
                        continue

                    for meeting in meetings:
                        days = _str(meeting.get("days")) or "TBA"
                        time = _str(meeting.get("time")) or None
                        bldg = _str(meeting.get("bldg")) or None
                        sessions.append({
                            **base,
                            "meetingTime": time,
                            "days": days,
                            "location": bldg,
                        })

    return sessions


def build_websoc_options(opts: dict) -> dict:
    options = {"term": opts.get("term")}
    for key in (
        "department", "ge", "instructorName", "courseNumber", "courseTitle",
        "sectionCodes", "days", "building", "room", "division", "sectionType",
        "startTime", "endTime", "fullCourses", "cancelledCourses",
    ):
        val = opts.get(key)
        if val is not None and val != "":
            options[key] = val
    return options


def fetch_class_sessions(search_options: dict) -> list:
    from . import anteater

    term = search_options.get("term")
    if not term:
        raise ValueError("search_options['term'] is required")

    options = build_websoc_options(search_options)
    if not any(options.get(k) for k in ("department", "ge", "instructorName", "sectionCodes")):
        raise ValueError("At least one of department, ge, instructorName, or sectionCodes is required")

    raw = anteater.fetch_websoc_from_anteater(search_options)
    return to_class_sessions(raw, term)
