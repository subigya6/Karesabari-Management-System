import os
import json
import re
import requests
from PIL import Image
from dataclasses import dataclass
import google.generativeai as genai

# ====================== CONFIG ======================
PLANTNET_KEY = "2b10kahQnuFH4C6zM7MOEe"
# Using the key from your working Streamlit version
GEMINI_KEY = "AIzaSyD2SAaUjdT41nG5qJHC7iA5h0-ulQjmcBA" 

genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

ORGAN_OPTIONS = ["auto", "leaf", "flower", "fruit", "bark"]

@dataclass
class DiagnosisResult:
    plant: str
    disease: str
    confidence: float
    remedy_english: str
    remedy_nepali: str
    organ: str
    reasoning: str = ""
    is_healthy: bool = False

class PlantDiagnosisEngine:
    def __init__(self):
        self.current_organ = "leaf"

    def set_organ(self, organ: str):
        if organ in ORGAN_OPTIONS:
            self.current_organ = organ

    def predict(self, image_path: str) -> DiagnosisResult:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = Image.open(image_path).convert("RGB")

        # Step 1: PlantNet Species
        species_data = self._plantnet_species(image_path)
        raw_plant = species_data.get("bestMatch", "Unknown Plant")
        cleaned_plant = self._clean_crop_name(species_data)

        # Step 2: PlantNet Disease
        disease_data = self._plantnet_disease(image_path)
        disease_results = disease_data.get("results", [{}])
        raw_disease = disease_results[0].get("name", "Unknown Disease")
        
        # Extract confidence from PlantNet if available, otherwise default to 0.85
        pn_score = disease_results[0].get("score", 0.85) if disease_results else 0.85

        # Step 3: Gemini Cross-check
        verified = self._gemini_crosscheck(img, raw_plant, raw_disease)
        final_plant = verified.get("verified_plant", cleaned_plant)
        final_disease = verified.get("verified_disease", raw_disease)

        # Step 4: Remedy 
        bilingual = self._get_bilingual_remedy(final_plant, final_disease)
        eng, nep = self._parse_bilingual(bilingual)

        is_healthy = "healthy" in final_disease.lower() or "no disease" in final_disease.lower()

        return DiagnosisResult(
            plant=final_plant.capitalize(),
            disease=final_disease,
            confidence=float(pn_score), 
            remedy_english=eng,
            remedy_nepali=nep,
            organ=self.current_organ,
            reasoning=verified.get("reasoning", "Analysis completed successfully."),
            is_healthy=is_healthy
        )

    # ====================== API CALLS ======================
    def _plantnet_species(self, image_path: str):
        url = f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_KEY}"
        with open(image_path, 'rb') as f:
            r = requests.post(url, files={'images': f}, data={'organs': [self.current_organ]}, timeout=20)
            r.raise_for_status()
            return r.json()

    def _plantnet_disease(self, image_path: str):
        url = f"https://my-api.plantnet.org/v2/diseases/identify?api-key={PLANTNET_KEY}"
        with open(image_path, 'rb') as f:
            r = requests.post(url, files={'images': f}, data={'organs': [self.current_organ]}, timeout=20)
            r.raise_for_status()
            return r.json()

    def _clean_crop_name(self, species_data: dict) -> str:
        try:
            results = species_data.get("results", [{}])
            common = results[0].get("species", {}).get("commonNames", [])
            if common:
                name = common[0].lower()
                return name.split()[0]
            raw = results[0].get("species", {}).get("scientificNameWithoutAuthor", "").lower()
            if "lycopersicum" in raw or "tomato" in raw: return "tomato"
            if "tuberosum" in raw or "potato" in raw: return "potato"
            return raw.split()[0]
        except:
            return "unknown"

    def _gemini_crosscheck(self, image, plantnet_plant: str, plantnet_disease: str):
        prompt = f"""You are a Nepali plant doctor. The image shows a **{self.current_organ}**.
PlantNet said:
- Plant: {plantnet_plant}
- Disease code/name: {plantnet_disease}

Return ONLY valid JSON:
{{
  "verified_plant": "tomato or potato or exact name",
  "verified_disease": "FULL disease name (expand TMV000 etc.)",
  "confidence": "high/medium/low",
  "reasoning": "short explanation"
}}"""
        response = gemini_model.generate_content([prompt, image])
        text = response.text.strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        try:
            return json.loads(match.group()) if match else {"verified_plant": plantnet_plant, "verified_disease": plantnet_disease}
        except:
            return {"verified_plant": plantnet_plant, "verified_disease": plantnet_disease}

    def _get_bilingual_remedy(self, plant: str, disease: str) -> str:
        try:
            narc_data = self._narc_remedies(plant)
            if "error" not in narc_data:
                match_prompt = f"""NARC diseases for {plant}: {json.dumps(narc_data)}\nDetected: {disease}\nReturn ONLY the key number of best match."""
                resp = gemini_model.generate_content(match_prompt)
                match = re.search(r'\d+', resp.text or "")
                best_key = match.group() if match else None
                
                if best_key and best_key in narc_data:
                    solution_text = narc_data.get(best_key, {}).get("Solution", "")
                    return self._make_short_bilingual_remedy(plant, disease, solution_text)
        except Exception as e:
            pass # Fallback to standard Gemini remedy on failure
            
        return self._make_short_bilingual_remedy(plant, disease)

    def _narc_remedies(self, crop: str):
        url = f"https://soil.narc.gov.np/crop/api/tsm/{crop.lower()}"
        r = requests.get(url, timeout=10)
        return r.json() if r.status_code == 200 else {"error": "No NARC data"}

    def _make_short_bilingual_remedy(self, plant: str, disease: str, original_text: str = None) -> str:
        if original_text:
            prompt = f"""Summarize this NARC remedy for {disease} on {plant} into **very short** practical advice for Kathmandu farmers.
Original text: {original_text[:800]}

Return EXACTLY this format (max 6 bullets):

**English Remedies:**
- Bullet 1
- Bullet 2
- Bullet 3
- Bullet 4 (prevention)

**Nepali Remedies:**
- Bullet 1 (Nepali)
- Bullet 2
- Bullet 3
- Bullet 4"""
        else:
            prompt = f"""Nepali agricultural expert in Kathmandu: very short remedies (max 6 bullets) for {disease} on {plant}.
Return EXACTLY this format:

**English Remedies:**
- Bullet 1 (specific + local name)
- Bullet 2
- Bullet 3
- Bullet 4 (prevention)

**Nepali Remedies:**
- Bullet 1 (Nepali)
- Bullet 2
- Bullet 3
- Bullet 4"""

        response = gemini_model.generate_content(prompt)
        return response.text.strip()

    def _parse_bilingual(self, text: str):
        eng = "No English remedy generated."
        nep = "कुनै उपचार सुझाव उपलब्ध छैन।"
        if "**English Remedies:**" in text:
            parts = text.split("**Nepali Remedies:**", 1)
            eng = parts[0].replace("**English Remedies:**", "").strip()
            if len(parts) > 1:
                nep = parts[1].strip()
        return eng, nep