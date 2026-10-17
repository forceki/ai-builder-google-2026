from pydantic import BaseModel

from app.models.document import DocType
from app.schemas.inspection import InspectionRecords
from app.schemas.mtc import MaterialCertificates
from app.schemas.ndt import NdtReports
from app.schemas.production import ProductionRecords
from app.schemas.weld import WeldingRecords

# One extraction schema per document type.
EXTRACTION_SCHEMAS: dict[DocType, type[BaseModel]] = {
    DocType.MTC: MaterialCertificates,
    DocType.WELD: WeldingRecords,
    DocType.NDT: NdtReports,
    DocType.INSPECTION: InspectionRecords,
    DocType.PRODUCTION: ProductionRecords,
}
