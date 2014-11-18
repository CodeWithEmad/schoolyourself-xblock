"""An XBlock that displays School Yourself reviews and may publish grades."""

import hmac
import urllib

from xblock.core import XBlock
from xblock.fields import Scope, String
from xblock.fragment import Fragment

from schoolyourself import SchoolYourselfXBlock


class SchoolYourselfReviewXBlock(SchoolYourselfXBlock):
    """
    This block renders a launcher button for a School Yourself review,
    which is rendered in an iframe. The block transmits the anonymous
    user ID and has a handler that receives information from School
    Yourself regarding the user's progress and mastery through the
    topic being shown.
    """
    has_children = False
    has_score = True
    weight = 1.0

    def student_view(self, context=None):
      """
      The primary view of the SchoolYourselfReviewXBlock, shown to students
      when viewing courses.
      """
      # Construct the URL we're going to stuff into the iframe once
      # it gets launched:
      url_params = self.get_partner_url_params(self.shared_key)
      url_params["module"] = self.module_id

      # Set up the screenshot URL:
      screenshot_url = "%s/page/screenshot/%s" % (self.base_url,
                                                  self.module_id)

      context = {
        "iframe_url": "%s/review/embed?%s" % (self.base_url,
                                              urllib.urlencode(url_params)),
        "module_title": self.module_title,
        "icon_url": self.runtime.local_resource_url(self,
                                                    "public/review_icon.png")
      }

      # Now actually render the fragment, which is just a button with
      # some JS code that handles the click event on that button.
      fragment = Fragment(self.render_template("review_student_view.html",
                                               context))

      # Load the common JS/CSS libraries:
      fragment.add_css_url(
        self.runtime.local_resource_url(self, "public/sylib.css"))
      fragment.add_javascript_url(
        self.runtime.local_resource_url(self, "public/sylib.js"))


      # And finally the embedded HTML/JS code:
      fragment.add_javascript(self.resource_string(
          "static/js/review_student_view.js"))
      fragment.add_css(self.resource_string(
          "static/css/student_view.css"))
      fragment.initialize_js("SchoolYourselfReviewStudentView")
      return fragment


    @XBlock.json_handler
    def handle_grade(self, data, suffix=""):
      """This is the handler that gets called when we receive grades.

      We will verify the message to make sure that it is signed and
      that the signature is valid. If everything is good, then we'll
      publish a "grade" event for this module.
      """
      mastery = data.get("mastery", None)
      user_id = data.get("user_id", None)
      signature = data.get("signature", None)
      if not mastery or not user_id or not signature:
        return

      # Check that the module ID we care about is actually in the data
      # that was sent.
      mastery_level = mastery.get(self.module_id, None)
      if mastery_level is None:
        return

      # Verify the signature.
      verifier = hmac.new(str(self.shared_key), user_id)
      for key in sorted(mastery):
        verifier.update(key)
        verifier.update("%.2f" % mastery[key])

      # If the signature is invalid, do nothing.
      if signature != verifier.hexdigest():
        return

      # If we got here, then everything checks out and we can submit
      # a grade for this module.
      self.runtime.publish(self, "grade",
                           { "value": mastery_level,
                             "max_value": 0.7 })


    @staticmethod
    def workbench_scenarios():
      """A canned scenario for display in the workbench."""
      return [
        ("SchoolYourselfReviewXBlock",
         """\
            <vertical_demo>
              <schoolyourself_review
                  base_url="http://localhost:9753"
                  module_id="algebra/multiplication"
                  shared_key="test"
              />
            </vertical_demo>
         """),
        ]