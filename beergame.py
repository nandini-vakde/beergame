
from otree.api import *
import json
import random

doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'BeerGame'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 10
    ROLES = ['Brewery', 'Distributor', 'Wholesaler', 'Retailer']
    BREWERY_ROLE = 'Brewery'
    DISTRIBUTOR_ROLE = 'Distributor'
    WHOLESALER_ROLE = 'Wholesaler'
    RETAILER_ROLE = 'Retailer'



class Subsession(BaseSubsession):
    def creating_session(self):
        # Assign roles to players
        if self.round_number == 1:
            for group in self.get_groups():
                players = group.get_players()
                roles = C.ROLES.copy()
                random.shuffle(roles)
                for player, role in zip(players, roles):
                    player.game_role = role

            # should allow access to specific groups, returns group matrix
            matrix = self.get_group_matrix()
            for row in matrix:
                row.reverse()
                self.set_group_matrix(matrix)
        else:
            self.group_like_round(1)


class Group(BaseGroup):
    # arrays to keep track of inventories and order amounts across rounds, previously in group class

    brewery_inventories = models.StringField(initial="")
    distributor_inventories = models.StringField(initial="")
    wholesaler_inventories = models.StringField(initial="")
    retailer_inventories = models.StringField(initial="")

    brewery_order_amounts = models.StringField(initial="")
    distributor_order_amounts = models.StringField(initial="")
    wholesaler_order_amounts = models.StringField(initial="")
    retailer_order_amounts = models.StringField(initial="")
    

    # functions to update arrays

    def update_order_amounts(self):
        for player in self.get_players():
            if player.game_role == C.BREWERY_ROLE:
                self.brewery_order_amounts.append(player.order_amount)
            elif player.game_role == C.DISTRIBUTOR_ROLE:
                self.distributor_order_amounts.append(player.order_amount)
            elif player.game_role == C.WHOLESALER_ROLE:
                self.wholesaler_order_amounts.append(player.order_amount)
            elif player.game_role == C.RETAILER_ROLE:
                self.retailer_order_amounts.append(player.order_amount)

    def update_inventories(self):
        for player in self.group.get_players():
            if player.game_role == C.BREWERY_ROLE:
                self.brewery_inventories.append(player.inventory)
            elif player.game_role == C.DISTRIBUTOR_ROLE:
                self.distributor_inventories.append(player.inventory)
            elif player.game_role == C.WHOLESALER_ROLE:
                self.wholesaler_inventories.append(player.inventory)
            elif player.game_role == C.RETAILER_ROLE:
                self.retailer_inventories.append(player.inventory)

    def set_payoffs(self):
        for player in self.group.get_players():
            inventory_cost = player.inventory * 1  # Cost per unit of inventory
            backorder_cost = player.backorder * 2  # Cost per unit of backorder

            # Assuming you want to minimize costs, you could treat the cost as a negative payoff
            player.cost = inventory_cost + backorder_cost
            player.payoff = -player.cost  # This sets the payoff to the negative cost for ranking or comparison purposes


class Player(BasePlayer):
    game_role = models.StringField(choices=C.ROLES)
    inventory = models.IntegerField(initial=50)
    order_amount = models.IntegerField(min=0)
    backorder = models.IntegerField(initial=0)
    cost = models.CurrencyField(initial=0)

    def calculate_inventory(self):
        # still need to calculate in transit, demand
        for player in self.group.get_players():
            if player.game_role == C.BREWERY_ROLE:
                if len(self.group.distributor_order_amounts) >= self.group.subsession.round_number - 1:
                    self.inventory = max(0, self.inventory - self.group.distributor_order_amounts[
                        self.group.subsession.round_number - 3] + self.group.brewery_order_amounts[
                                             self.group.subsession.round_number - 2])
                    self.backorder = self.backorder + (self.inventory - self.group.distributor.order_amount)
            elif player.game_role == C.DISTRIBUTOR_ROLE:
                if len(self.group.wholesaler_order_amounts) >= self.group.subsession.round_number - 1:
                    self.inventory = max(0, self.inventory - self.group.wholesaler_order_amounts[
                        self.group.subsession.round_number - 3] + self.group.distributor_order_amounts[
                                             self.group.subsession.round_number - 3])
                    self.backorder = self.backorder + (self.inventory - self.group.wholesaler.order_amount)
            elif player.game_role == C.WHOLESALER_ROLE:
                if len(self.group.retailer_order_amounts) >= self.group.subsession.round_number - 1:
                    self.inventory = max(0, self.inventory - self.group.retailer_order_amounts[
                        self.group.subsession.round_number - 3] + self.group.wholesaler_order_amounts[
                                             self.group.subsession.round_number - 3])
                    self.backorder = self.backorder + (self.inventory - self.group.retailer.order_amount)
            elif player.game_role == C.RETAILER_ROLE:
                self.inventory = max(0, self.inventory - 25 + self.group.retailer_order_amounts[
                    self.group.subsession.round_number - 3])
                self.backorder = max(0, self.backorder + (self.inventory - 25))


class Introduction(Page):
    def vars_for_template(self):
        return {
            'role': "Test Role"
            # self.player.game_role
        }


class OrderPage(Page):
    form_model = 'player'
    form_fields = ['order_amount']

    def before_next_page(self, timeout_happened=False):
        for player in self.group.get_players(): 
            if isinstance(player.order_amount, int) and 0 < player.order_amount < 10000:
                self.group.update_order_amounts()
                self.group.update_inventories()
                player.calculate_inventory()

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = 'set_payoffs'


class Results(Page):
    pass


page_sequence = [Introduction, OrderPage, ResultsWaitPage, Results]
