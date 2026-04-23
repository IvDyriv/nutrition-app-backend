from rest_framework.test import APITestCase
from nutrition.models import Product
from nutrition.tests.constants import NOT_EXISTING_URL, DETAILED_PRODUCTS_URL, LIST_PRODUCTS_URL


class TestValidRequests(APITestCase):
    """
    We test that we get 200 when all query parameters are valid
    with correct HTTP method (GET) and existing URLs
    """
    def setUp(self):
        self.product = Product.objects.create(
            name="TestName",
            tags=["lo_cal",],
            properties=["hi-prot",]
        )

    def test_list_get_url(self):
        response = self.client.get(LIST_PRODUCTS_URL)

        self.assertEqual(response.status_code, 200)

    def test_detailed_get_url(self):
        response = self.client.get(
            DETAILED_PRODUCTS_URL.format(product_id=self.product.id)
        )

        self.assertEqual(response.status_code, 200)

    def test_list_valid_search_params(self):
        data = {
            "search": "test"
        }
        response = self.client.get(LIST_PRODUCTS_URL, data=data)

        self.assertEqual(response.status_code, 200)

    def test_list_valid_page_params(self):
        data = {
            "page": 1
        }
        response = self.client.get(LIST_PRODUCTS_URL, data=data)

        self.assertEqual(response.status_code, 200)

    def test_list_valid_tag_params(self):
        data = {
            "tag": "lo_cal"
        }
        response = self.client.get(LIST_PRODUCTS_URL, data=data)

        self.assertEqual(response.status_code, 200)

    def test_list_valid_props_params(self):
        data = {
            "prop": "hi-prot"
        }
        response = self.client.get(LIST_PRODUCTS_URL, data=data)

        self.assertEqual(response.status_code, 200)

    def test_list_valid_all_params(self):
        data = {
            "search": "test",
            "page": 1,
            "tag": "lo_cal",
            "prop": "hi-prot"
        }
        response = self.client.get(LIST_PRODUCTS_URL, data=data)

        self.assertEqual(response.status_code, 200)