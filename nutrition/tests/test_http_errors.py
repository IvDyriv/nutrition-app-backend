from rest_framework.test import APITestCase

NOT_EXISTING_URL = "/api/v1/notexist/"

class TestEndpointNotExist(APITestCase):
    """
    We test whether we get a 404 status code when we try to access a non-existent URL,
    regardless of the HTTP method and regardless of the request body.
    """

    def test_get_url_not_exist(self):
        response = self.client.get(NOT_EXISTING_URL)

        self.assertEqual(response.status_code, 404)

    def test_post_url_not_exist(self):
        response = self.client.post(NOT_EXISTING_URL)

        self.assertEqual(response.status_code, 404)

    def test_put_url_not_exist(self):
        response = self.client.put(NOT_EXISTING_URL)

        self.assertEqual(response.status_code, 404)

    def test_delete_url_not_exist(self):
        response = self.client.delete(NOT_EXISTING_URL)

        self.assertEqual(response.status_code, 404)

    def test_patch_url_not_exist(self):
        response = self.client.patch(NOT_EXISTING_URL)

        self.assertEqual(response.status_code, 404)

    def test_with_body_url_not_exist(self):
        data = {"test": "test"}
        response = self.client.post(NOT_EXISTING_URL, data=data, format="json")

        self.assertEqual(response.status_code, 404)