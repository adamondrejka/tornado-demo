import tornado.web

__author__ = 'adam'


class NewsModule(tornado.web.UIModule):
    def render(self):
        last_news = [
            {"title": "Novinka 1", "content": "Obsah novinky..." },
            {"title": "Novinka 2", "content": "Obsah novinky..." },
            {"title": "Novinka 3", "content": "Obsah novinky..." },
        ]

        return self.render_string("templates/uimodules/news_module.html", news=last_news)