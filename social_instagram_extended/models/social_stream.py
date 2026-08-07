import logging

from odoo import models


_logger = logging.getLogger(__name__)


class SocialStream(models.Model):
    _inherit = "social.stream"

    def _fetch_instagram_posts(self):
        """Keep a captionless Instagram post from breaking the whole dashboard."""
        try:
            return super()._fetch_instagram_posts()
        except TypeError as error:
            if str(error) != 'can only concatenate str (not "NoneType") to str':
                raise

            _logger.warning(
                "Instagram returned a post without a caption for stream(s) %s; "
                "skipping this refresh to keep Social Marketing available.",
                self.ids,
            )
            return self.env["social.stream.post"]
