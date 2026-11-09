from fastapi import APIRouter

from ..ai.muse_image import MuseImageProvider
from ..ai.muse_spark import MuseSparkProvider
from ..ai.sam import SAMProvider
from ..core.config import get_settings
from ..schemas import ProviderStatus

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderStatus])
def providers():
    s = get_settings()
    out = []
    for provider, model in ((SAMProvider(), s.sam_model),
                            (MuseImageProvider(), s.image_model),
                            (MuseSparkProvider(), s.spark_model)):
        state, message = provider.state()
        out.append(ProviderStatus(name=provider.name, state=state.value, message=message, model=model))
    return out
