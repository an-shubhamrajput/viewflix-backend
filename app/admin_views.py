from flask_admin import AdminIndexView, expose


class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        return super().index()

from flask_admin import AdminIndexView, expose

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        print("Rendering admin index", flush=True)
        # You can pass variables to your template here if needed
        return self.render('/admin/index.html')


# import logging
# logging.basicConfig(level=logging.DEBUG)
# from flask_admin import AdminIndexView, expose

# class MyAdminIndexView(AdminIndexView):
#     @expose('/')
#     def index(self):
#         app.logger.debug("Rendering admin index")
#         return self.render('admin/index.html')
# /home/nexususer/Desktop/Shubham/ViewFlix UI/flask-backend/templates/admin/index.html