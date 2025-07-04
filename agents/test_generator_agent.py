import openai
from typing import List, Dict
import json
from models.test_case import TestCase, TestStep, TestType, Priority
from config.settings import settings
# from config.prompts import TEST_GENERATOR_PROMPT
from core.rag_engine import RAGEngine

class TestGeneratorAgent:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai.OpenAI()
        self.rag_engine = RAGEngine()
        
    def generate_test_cases_with_rag(self, ui_flows: List[str]) -> List[TestCase]:
        """Generate test cases using RAG for each UI flow"""
        all_test_cases = []
        
        for flow in ui_flows:
            # Use RAG to get relevant context
            relevant_docs = self.rag_engine.search_by_ui_component(flow)
            context = self._build_context_from_docs(relevant_docs)
            
            # Generate test cases for this specific flow
            test_cases = self._generate_flow_specific_tests(flow, context)
            all_test_cases.extend(test_cases)
            
        return all_test_cases
    
    def _build_context_from_docs(self, docs: List) -> str:
        """Build context string from retrieved documents"""
        context_parts = []
        
        for doc in docs:
            # Include timestamp info if available
            metadata = doc.metadata
            if 'start_time' in metadata:
                context_parts.append(
                    f"[{metadata['start_time']:.1f}s] {doc.page_content}"
                )
            else:
                context_parts.append(doc.page_content)
        
        return "\n\n".join(context_parts)
    
    def _generate_flow_specific_tests(self, flow: str, context: str) -> List[TestCase]:
        """Generate test cases for specific UI flow using retrieved context"""
        
        prompt = f"""
        Based on this video transcript context about {flow}:
        
        CONTEXT:
        {context}
        
        Generate comprehensive test cases for the {flow} functionality including:
        1. Happy path scenarios
        2. Edge cases (invalid inputs, network issues)
        3. Accessibility considerations
        4. Cross-browser compatibility
        5. Error handling scenarios
        
        Format as JSON with the following structure:
        {{
            "test_cases": [
                {{
                    "id": "unique_test_id",
                    "title": "Test case title",
                    "description": "Detailed description",
                    "test_type": "functional|edge_case|accessibility|performance",
                    "priority": "high|medium|low",
                    "preconditions": ["condition1", "condition2"],
                    "steps": [
                        {{
                            "action": "click|type|wait|assert",
                            "selector": "CSS selector",
                            "value": "input value (if applicable)",
                            "expected_result": "expected outcome",
                            "wait_condition": "wait condition (if applicable)"
                        }}
                    ],
                    "expected_results": ["result1", "result2"],
                    "tags": ["tag1", "tag2"],
                    "browser_compatibility": ["chrome", "firefox", "safari"]
                }}
            ]
        }}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are QAgenie, a thorough AI QA assistant specializing in frontend testing."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        test_cases_data = json.loads(response.choices[0].message.content)
        return self._convert_to_test_cases(test_cases_data)