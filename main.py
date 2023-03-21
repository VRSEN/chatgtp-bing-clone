from googleapiclient.discovery import build
import openai
import gradio as gr
import os

# https://platform.openai.com/account/api-keys
openai.api_key = os.environ.get("OPENAI_API_KEY")


class GoogleChat():
    def __init__(self):
        # init google search engine
        self.service = build(
            # https://developers.google.com/custom-search/v1/introduction
            "customsearch", "v1", developerKey=""
        )

    def _search(self, query):
        # call google search api
        response = (
            self.service.cse()
            .list(
                q=query,
                cx="", # https://programmablesearchengine.google.com/controlpanel/all
            )
            .execute()
        )
        return response['items']

    def _get_search_query(self, history, query):
        # only use user messages
        # assistant messages and not relevant for response
        messages = [{"role": "system",
                     "content": "You are an assistant that helps to convert text into a web search engine query. "
                                "You output only 1 query for the latest message and nothing else."}]

        for message in history:
            messages.append({"role": "user", "content": message[0]})

        messages.append({"role": "user", "content": "Based on my previous messages, "
                                                    "what is the most relevant web search query for the text below?\n\n"
                                                    "Text: " + query + "\n\n"
                                                                       "Query:"})

        search_query = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,
        )['choices'][0]['message']['content']

        return search_query.strip("\"")

    def run_text(self, history, query):
        search_query = self._get_search_query(history, query)

        print("Search query: ", search_query)

        # add system message to the front
        messages = [{"role": "system",
                     "content": "You are a search assistant that answers questions based on search results and "
                                "provides links to relevant parts of your answer."}]

        # unpack history into messages
        for message in history:
            messages.append({"role": "user", "content": message[0]})
            if message[1]:
                messages.append({"role": "assistant", "content": message[1]})

        # construct prompt from search results
        prompt = "Answer query using the information from the search results below: \n\n"
        results = self._search(search_query)
        for result in results:
            prompt += "Link: " + result['link'] + "\n"
            prompt += "Title: " + result['title'] + "\n"
            prompt += "Content: " + result['snippet'] + "\n\n"
        prompt += "Query: " + query
        messages.append({"role": "user", "content": prompt})
        # print(prompt)

        # generate response
        response = openai.ChatCompletion.create(
            model="gpt-4",  # change to gpt-3.5-turbo if don't have access
            messages=messages,
            temperature=0.4,
        )['choices'][0]['message']['content']

        # only add query and response to history
        # the context is not needed
        history.append((query, response))

        return history


if __name__ == '__main__':
    bot = GoogleChat()

    # ui
    with gr.Blocks(css="#chatbot .overflow-y-auto{height:500px}") as demo:
        chatbot = gr.Chatbot([], elem_id="chatbot", label="GPT-4 Bing Clone").style(height=160)
        with gr.Row():
            with gr.Column(scale=0.85):
                txt = gr.Textbox(show_label=False, placeholder="What do you want to know?").style(
                    container=False)
            with gr.Column(scale=0.15, min_width=0):
                clear = gr.Button("Clear")

        txt.submit(bot.run_text, [chatbot, txt], chatbot)
        txt.submit(lambda: "", None, txt)
        clear.click(lambda: [], None, chatbot)
        demo.launch()
