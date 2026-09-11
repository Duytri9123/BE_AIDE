# Import Base from models
from app.models.base import Base

# Import tất cả các model tại đây để Alembic có thể tự động phát hiện (autodiscover)
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.refresh_token import RefreshToken
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.project_version import ProjectVersion
from app.models.ai_connection import AiConnection
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel
from app.models.prompt_template import PromptTemplate
from app.models.system_setting import SystemSetting
from app.models.notification import Notification
from app.models.page_content import PageContent
from app.models.brand import Brand
from app.models.device_category import DeviceCategory
from app.models.device_series import DeviceSeries
from app.models.device_model import DeviceModel
from app.models.user_device_library import UserDeviceLibrary
from app.models.user_library_file import UserLibraryFile
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.token_log import TokenLog
from app.models.activity_log import ActivityLog
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration
