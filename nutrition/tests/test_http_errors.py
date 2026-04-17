from rest_framework.test import APITestCase

from nutrition.models import Product

NOT_EXISTING_URL = "/api/v1/notexist/"
LIST_PRODUCTS_URL = "/api/v1/products/"
DETAILED_PRODUCTS_URL = "/api/v1/products/{product_id}/"


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

class TestMethodsNotAllowed(APITestCase):
    """
    We test whether we get a 405 status code when we try to access existing endpoints
    with HTTP methods that are not allowed (PUT, POST, DELETE, PATCH),
    both for the list and detailed URLs, and regardless of the request body.
    """
    def setUp(self):
        self.product = Product.objects.create(name="Test")

    def test_list_put_method_not_allowed(self):
        response = self.client.put(LIST_PRODUCTS_URL)

        self.assertEqual(response.status_code, 405)

    def test_detailed_put_method_not_allowed(self):
        response = self.client.put(
            DETAILED_PRODUCTS_URL.format(product_id=self.product.id)
        )

        self.assertEqual(response.status_code, 405)

    def test_list_post_method_not_allowed(self):
        response = self.client.post(LIST_PRODUCTS_URL)

        self.assertEqual(response.status_code, 405)

    def test_detailed_post_method_not_allowed(self):
        response = self.client.post(
            DETAILED_PRODUCTS_URL.format(product_id=self.product.id)
        )

        self.assertEqual(response.status_code, 405)

    def test_list_delete_method_not_allowed(self):
        response = self.client.delete(LIST_PRODUCTS_URL)

        self.assertEqual(response.status_code, 405)

    def test_detailed_delete_method_not_allowed(self):
        response = self.client.delete(
            DETAILED_PRODUCTS_URL.format(product_id=self.product.id)
        )

        self.assertEqual(response.status_code, 405)

    def test_list_patch_method_not_allowed(self):
        response = self.client.patch(LIST_PRODUCTS_URL)

        self.assertEqual(response.status_code, 405)

    def test_detailed_patch_method_not_allowed(self):
        response = self.client.patch(
            DETAILED_PRODUCTS_URL.format(product_id=self.product.id)
        )

        self.assertEqual(response.status_code, 405)

    def test_list_with_body_method_not_allowed(self):
        data = "testdata"
        response = self.client.put(LIST_PRODUCTS_URL, data=data, format="json")

        self.assertEqual(response.status_code, 405)

    def test_detailed_with_body_method_not_allowed(self):
        data = "testdata"
        response = self.client.put(
            DETAILED_PRODUCTS_URL.format(product_id=self.product.id),
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, 405)