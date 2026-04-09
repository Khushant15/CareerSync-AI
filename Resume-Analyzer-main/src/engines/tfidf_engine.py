import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords

# Download stopwords on first run
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class TFIDFEngine:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=list(self.stop_words),
            ngram_range=(1, 2)  # Capture both unigrams and bigrams
        )

    def preprocess_text(self, text):
        """Cleans and tokenizes text."""
        # Lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        return text

    def analyze(self, resume_text, jd_text):
        """
        Main matching logic:
        1. Preprocess
        2. Vectorize using TF-IDF
        3. Compute Cosine Similarity
        4. Extract Keyword Importance (Explainability)
        """
        if not jd_text:
            return {"match_score": 0, "matched_keywords": [], "missing_keywords": [], "explanation": "No Job Description provided."}

        # 1. Preprocess
        resume_clean = self.preprocess_text(resume_text)
        jd_clean = self.preprocess_text(jd_text)

        # 2. Vectorize
        # We fit on both to create a shared vocabulary space
        tfidf_matrix = self.vectorizer.fit_transform([resume_clean, jd_clean])
        feature_names = self.vectorizer.get_feature_names_out()

        # 3. Similarity Score
        cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        match_score = round(float(cosine_sim) * 100, 2)

        # 4. Keyword Importance & Explainability
        # Get TF-IDF scores for the JD (to see what's 'important')
        jd_vector = tfidf_matrix[1].toarray()[0]
        resume_vector = tfidf_matrix[0].toarray()[0]

        # Identify top keywords in JD by TF-IDF weight
        # These are tokens that are frequent in JD but theoretically unique in general corpora
        sorted_jd_indices = np.argsort(jd_vector)[::-1]
        top_n = min(20, len(sorted_jd_indices))
        
        important_keywords = []
        matched_keywords = []
        missing_keywords = []

        for i in sorted_jd_indices[:top_n]:
            keyword = feature_names[i]
            importance = jd_vector[i]
            
            if importance > 0:
                important_keywords.append({"word": keyword, "score": round(float(importance), 4)})
                
                # Check if it was present in resume (above a tiny threshold to avoid noise)
                if resume_vector[i] > 0:
                    matched_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)

        return {
            "match_score": match_score,
            "matched_keywords": matched_keywords[:10],  # Return top 10
            "missing_keywords": missing_keywords[:10],
            "importance_ranking": important_keywords[:10],
            "explanation": f"The model identifies a {match_score}% semantic overlap between your resume and the job description based on Term Frequency-Inverse Document Frequency (TF-IDF)."
        }
