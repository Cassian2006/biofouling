from pydantic import BaseModel


class StudyArea(BaseModel):
    west: float = 102.90
    south: float = 0.80
    east: float = 104.90
    north: float = 1.85


class Settings(BaseModel):
    project_name: str = "biofouling"
    study_area: StudyArea = StudyArea()


settings = Settings()

