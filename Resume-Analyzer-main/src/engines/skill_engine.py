import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Detailed Skill Taxonomy
SKILL_TAXONOMY = {
    "technical": [
        "python", "java", "javascript", "typescript", "react", "angular", "vue", "node.js", 
        "flask", "django", "express", "sql", "postgresql", "mongodb", "rest api", "graphql", 
        "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ci/cd", "jenkins", 
        "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "c++", "c#", "go", "rust", 
        "ruby", "php", "swift", "kotlin", "html", "css", "sass", "webpack", "microservices",
        "solidity", "ethers.js", "smart contracts", "ansible", "prometheus", "grafana",
        "penetration testing", "wireshark", "metasploit", "cryptography", "firewalls",
        "embedded c", "rtos", "microcontrollers", "verilog", "power bi", "tableau", "statistics",
        "selenium", "cypress", "appium", "redhat", "unix", "shell scripting"
    ],
    "soft": [
        "leadership", "communication", "teamwork", "problem solving", "critical thinking", 
        "adaptability", "time management", "conflict resolution", "creativity", "emotional intelligence",
        "mentoring", "public speaking", "collaboration", "decision making", "interpersonal", "agile",
        "scrum", "kanban", "product discovery", "stakeholder management", "strategic planning",
        "negotiation", "active listening", "empathy", "storytelling", "user empathy"
    ],
    "tools": [
        "git", "github", "gitlab", "jira", "confluence", "trello", "figma", "sketch", "adobe xd", 
        "postman", "slack", "vscode", "intellij", "pycharm", "eclipse", "excel", "tableau", 
        "power bi", "notion", "docker desktop", "linux", "bash", "npm", "yarn", "circleci",
        "heroku", "netlify", "vercel", "splunk", "elastic search", "kibana", "metabase",
        "google analytics", "mixpanel", "hotjar", "canva", "invision", "zeplin"
    ]
}

class SkillEngine:
    def __init__(self):
        # We create a pseudo-corpus to give TF-IDF context (typical professional density)
        self.corpus = [
            " ".join(SKILL_TAXONOMY["technical"] + SKILL_TAXONOMY["soft"] + SKILL_TAXONOMY["tools"]),
            "professional experience with python and aws using git for development and communication",
            "leadership and teamwork are key soft skills in any technical environment using agile"
        ]
        self.vectorizer = TfidfVectorizer(lowercase=True, stop_words='english')
        self.vectorizer.fit(self.corpus)

    def analyze_resume(self, text):
        """Analyzes resume text using weighted keyword matching and TF-IDF."""
        text = text.lower()
        results = {}
        detected_skills = { "technical": [], "soft": [], "tools": [] }
        
        # 1. TF-IDF Scoring
        # Transform the resume text in the context of our skill corpus
        try:
            tfidf_matrix = self.vectorizer.transform([text])
            feature_names = self.vectorizer.get_feature_names_out()
            dense = tfidf_matrix.todense().tolist()[0]
            tfidf_scores = {feature_names[i]: dense[i] for i in range(len(feature_names)) if dense[i] > 0}
        except:
            tfidf_scores = {}

        # 2. Categorize and Normalize
        categories = ["technical", "soft", "tools"]
        for cat in categories:
            possible_skills = SKILL_TAXONOMY[cat]
            found = []
            score_sum = 0
            
            for skill in possible_skills:
                # Direct Match or Regex for flexibility (e.g., "node.js" vs "node")
                if re.search(rf"\b{re.escape(skill)}\b", text):
                    found.append(skill)
                    # Use TF-IDF weight if exists, otherwise default to a base frequency weight
                    weight = tfidf_scores.get(skill.lower(), 0.1) 
                    score_sum += weight

            # Normalization logic:
            # We normalize based on the category's typical density
            # A score of 100 means they hit a high threshold of keywords in that category
            threshold = len(possible_skills) * 0.25 # If they have 25% of the dictionary, they are elite
            raw_score = (len(found) / threshold) * 100 if threshold > 0 else 0
            
            results[cat] = min(round(raw_score, 1), 100)
            detected_skills[cat] = found

        # Identify Strongest/Weakest
        sorted_cats = sorted(results.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "scores": results,
            "detected": detected_skills,
            "strongest": sorted_cats[0][0],
            "weakest": sorted_cats[-1][0],
            "explanation": f"The analysis identifies {sorted_cats[0][0].upper()} as your most developed quadrant."
        }
