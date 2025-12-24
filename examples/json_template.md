# JSON Input Template

This file shows the expected JSON structure for the syllabus generator.

```json
{
    "document_type": "syllabus",
    "index": ["Course Information", "Topics Covered", "Grading Policy", "Main Dates"],
    "sections": [
        {
            "id": 0,
            "title": "Course Information",
            "content": {
                "course_name": "Your Course Name",
                "instructor": "Instructor Name",
                "credits": 3,
                "description": "Course description here"
            }
        },
        {
            "id": 1,
            "title": "Topics Covered",
            "content": {
                "week_1": ["Topic 1", "Topic 2"],
                "week_2": ["Topic 3", "Topic 4"]
            }
        }
    ]
}
```

## Fields

- **document_type**: The type of document (e.g., "syllabus", "lecture_notes", "course_outline")
- **index**: Array of main topic titles
- **sections**: Array of section objects
  - **id**: Unique identifier (integer, starting from 0)
  - **title**: Section title (should match an item in the index)
  - **content**: Can be:
    - Dictionary with key-value pairs
    - List of items
    - String with text content
