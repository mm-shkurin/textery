class TestProjectItemShape:
    """Scenario 1.1: the feed row's shape is complete and total.

    Given the contract declares nine required fields on a feed row
    When the domain value object that carries them is declared
    Then it declares exactly those nine
    And none of them may be omitted at a call site.
    """

    def test_should_declare_exactly_the_contracts_fields(self, project_item_shape_statements):
        project_item_shape_statements.assert_the_row_declares_exactly_the_contract_fields()

    def test_should_leave_every_field_required(self, project_item_shape_statements):
        project_item_shape_statements.assert_no_field_carries_a_default()
