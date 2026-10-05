import os
from plant_diagnosis_engine import PlantDiagnosisEngine, DiagnosisResult

class LeafAnalyzer:
    """Wrapper that accesses the real PlantNet + Gemini engine"""

    def __init__(self):
        self._engine = PlantDiagnosisEngine()

    def set_organ(self, organ: str):
        self._engine.set_organ(organ)

    def predict(self, image_path: str) -> DiagnosisResult:
        return self._engine.predict(image_path)

    def predict_from_pil(self, pil_image) -> DiagnosisResult:
        temp_path = "temp_upload.jpg"
        pil_image.save(temp_path)
        result = self.predict(temp_path)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return result