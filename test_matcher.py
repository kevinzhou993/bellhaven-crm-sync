import unittest

from matcher import build_proposals


PARENT = {"id": "parent", "name": "Bellhaven Senior Living (Parent Account)"}


def location(name="Bellhaven Test", street="1 Main St", city="Akron", state="OH", zip_code="44301"):
    return {"name": name, "street": street, "city": city, "state": state, "zip": zip_code,
            "care_offerings": ["Assisted Living"], "source_url": "/communities/test"}


def account(**overrides):
    value = {"id": "old", "name": "Bellhaven Test", "street": "1 Main Street", "city": "Akron",
             "state": "OH", "zip": "44301", "parent_id": "parent", "status": "Active",
             "care_type": "Assisted Living", "lifetime_revenue": 0, "outstanding_ar": 0}
    value.update(overrides)
    return value


class MatcherTests(unittest.TestCase):
    def test_name_and_geography_allow_address_correction(self):
        props = build_proposals([location(street="9 New Rd")], [PARENT, account(street="1 Old Rd")])
        self.assertEqual(props[0]["action"], "update")
        self.assertEqual(props[0]["changes"]["billing_street"], "9 New Rd")

    def test_same_name_in_different_city_is_not_repurposed(self):
        props = build_proposals([location(city="Hudson", zip_code="44236")],
                                [PARENT, account(city="Denver", state="CO", zip="80202")])
        self.assertEqual(props[0]["action"], "create")

    def test_chow_preserves_old_account_when_revenue_and_ar_exist(self):
        old = account(parent_id="other", lifetime_revenue=5000, outstanding_ar=100)
        props = build_proposals([location()], [PARENT, old])
        self.assertEqual(props[0]["action"], "chow")
        self.assertEqual(props[0]["old_account_changes"]["chow_current_account"], "$NEW_ACCOUNT_ID")

    def test_zero_ar_allows_direct_reparent(self):
        old = account(parent_id="other", lifetime_revenue=5000, outstanding_ar=0)
        props = build_proposals([location()], [PARENT, old])
        self.assertEqual(props[0]["action"], "update")
        self.assertEqual(props[0]["changes"]["parent_id"], "parent")


if __name__ == "__main__":
    unittest.main()
