import os
import config
os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY
from crewai import Agent, Task, Crew
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")

listing_writer = Agent(
    role="Listing Writer",
    goal="Create compelling and clear product listings based on raw data in chinese",
    backstory="An e-commerce expert that writes high-converting listings.",
    verbose=True,
    llm=llm
)

reviewer = Agent(
    role="Reviewer",
    goal="Review product listings for tone, clarity, and correctness",
    backstory="A grammar and UX expert ensuring everything sounds natural.",
    verbose=True,
    llm=llm
)

def run_listing_pipeline(product_data):
    task1 = Task(
        description=f"Write a listing for this product: {product_data} in chinese",
        expected_output="Well-formatted product listing in markdown.",
        agent=listing_writer
    )
    task2 = Task(
        description="Review and improve the listing written above.",
        expected_output="Polished final product listing.",
        agent=reviewer
    )

    crew = Crew(
        agents=[listing_writer, reviewer],
        tasks=[task1, task2],
        verbose=True
    )
    result = crew.kickoff()
    return result.raw
