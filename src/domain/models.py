from typing import Optional, List, TypedDict


class UserProfile(TypedDict):
    userid: int
    fullname: Optional[str]


class CourseInfo(TypedDict, total=False):
    id: int
    fullname: Optional[str]
    shortname: Optional[str]
    progress_percent: Optional[int]
    startdate: Optional[int]
    enddate: Optional[int]
    viewurl: Optional[str]


class ActivityInfo(TypedDict, total=False):
    cmid: Optional[int]
    modtype: Optional[str]
    name: str
    url: str
    dates: List[str]
    section: Optional[str]


class CourseSection(TypedDict):
    section: str
    activities: List[ActivityInfo]


class FileAttachment(TypedDict):
    name: str
    url: str


class AssignmentDetail(TypedDict):
    title: Optional[str]
    dates: List[str]
    submission_status: Optional[str]
    grade: Optional[str]
    description: Optional[str]
    files: List[FileAttachment]
    text_excerpt: str
    url: str


class DownloadResult(TypedDict):
    saved_to: str
    size_bytes: int


class CalendarEvent(TypedDict, total=False):
    name: Optional[str]
    type: Optional[str]
    module: Optional[str]
    timestart_epoch: Optional[int]
    time: Optional[str]
    course_id: Optional[int]
    url: Optional[str]
    description: str


class SessionStatus(TypedDict, total=False):
    valid: bool
    reason: Optional[str]
    userid: Optional[int]


class SetSessionResult(TypedDict, total=False):
    status: str
    userid: Optional[int]
    saved_to: str
    note: str
