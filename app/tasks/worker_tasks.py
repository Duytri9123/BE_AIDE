from app.tasks.celery_app import celery_app

@celery_app.task
def process_cad_file(file_path: str, project_id: str):
    # heavy CAD parsing
    pass

@celery_app.task
def run_ai_analysis(session_id: str, files: list, provider: str, model: str):
    # AI analysis in background
    pass

@celery_app.task
def generate_excel_export(project_id: str, scope: str, layout: str):
    # Excel generation
    pass

@celery_app.task
def enhance_image(image_path: str):
    # image enhancement
    pass
