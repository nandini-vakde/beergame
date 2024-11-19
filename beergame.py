
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
                    if player.game_role is None:
                        player.game_role = role

            # should allow access to specific groups, returns group matrix
            matrix = self.get_group_matrix()
            for row in matrix:
                row.reverse()
                self.set_group_matrix(matrix)
        else:
            self.group_like_round(1)


class Group(BaseGroup):
    # arrays to keep track of inventories and order amounts across rounds

    def update_order_amounts(self):
        session = self.session  # Access session dynamically
        if 'brewery_order_amounts' not in session.vars:
            session.vars['brewery_order_amounts'] = []
        if 'distributor_order_amounts' not in session.vars:
            session.vars['distributor_order_amounts'] = []
        if 'wholesaler_order_amounts' not in session.vars:
            session.vars['wholesaler_order_amounts'] = []
        if 'retailer_order_amounts' not in session.vars:
            session.vars['retailer_order_amounts'] = []

        for player in self.get_players():
            if player.id_in_group == 1:
                session.vars['brewery_order_amounts'].append(player.order_amount)
            elif player.id_in_group == 2:
                session.vars['distributor_order_amounts'].append(player.order_amount)
            elif player.id_in_group == 3:
                session.vars['wholesaler_order_amounts'].append(player.order_amount)
            elif player.id_in_group == 4:
                session.vars['retailer_order_amounts'].append(player.order_amount)

    def update_inventories(self):
        session = self.session  # Access session dynamically
        if 'brewery_inventories' not in session.vars:
            session.vars['brewery_inventories'] = []
        if 'distributor_inventories' not in session.vars:
            session.vars['distributor_inventories'] = []
        if 'wholesaler_inventories' not in session.vars:
            session.vars['wholesaler_inventories'] = []
        if 'retailer_inventories' not in session.vars:
            session.vars['retailer_inventories'] = []

        for player in self.get_players():
            if player.id_in_group == 1:
                session.vars['brewery_inventories'].append(player.inventory)
            elif player.id_in_group == 2:
                session.vars['distributor_inventories'].append(player.inventory)
            elif player.id_in_group == 3:
                session.vars['wholesaler_inventories'].append(player.inventory)
            elif player.id_in_group == 4:
                session.vars['retailer_inventories'].append(player.inventory)

    def set_payoffs(self):
        for player in self.get_players():
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

    #still need to calculate in transit & demand

    def calculate_inventory(self):
        session = self.group.session.vars
        round_num = self.group.subsession.round_number

        if self.id_in_group == 1 & round_num >= 2:  # Brewery
            if len(session['distributor_order_amounts']) >= round_num - 2 and len(session['brewery_order_amounts']) >= round_num - 1:
                if round_num == 3:
                    brewery_order = session['brewery_order_amounts'][round_num - 2]
                    self.inventory = brewery_order
                elif round_num > 3:
                    distributor_order = session['distributor_order_amounts'][round_num - 3]
                    brewery_order = session['brewery_order_amounts'][round_num - 2]
                    self.inventory = max(0, self.inventory - distributor_order + brewery_order)
                    self.backorder += max(0, distributor_order - self.inventory)

        elif self.id_in_group == 2:  # Distributor
           if round_num >= 4:
               if len(session['wholesaler_order_amounts']) >= round_num - 2 and len(session['distributor_order_amounts']) >= round_num - 3:
                    wholesaler_order = session['wholesaler_order_amounts'][round_num - 3]
                    distributor_order = session['distributor_order_amounts'][round_num - 3]
                    self.inventory = max(0, self.inventory - wholesaler_order + distributor_order)
                    self.backorder += max(0, wholesaler_order - self.inventory)
               
        elif self.id_in_group == 3:  # Wholesaler
            if round_num >= 4:
                if len(session['retailer_order_amounts']) >= round_num - 2 and len(session['wholesaler_order_amounts']) >= round_num - 3:
                    retailer_order = session['retailer_order_amounts'][round_num - 3]
                    wholesaler_order = session['wholesaler_order_amounts'][round_num - 3]
                    self.inventory = max(0, self.inventory - retailer_order + wholesaler_order)
                    self.backorder += max(0, retailer_order - self.inventory)

        elif self.id_in_group == 4:  # Retailer
            if round_num >= 4:
                if len(session['retailer_order_amounts']) >= round_num - 3:
                    retailer_order = session['retailer_order_amounts'][round_num - 3]
                    self.inventory = max(0, self.inventory - 25 + retailer_order)
                    self.backorder += max(0, 25 - self.inventory)
                    

class Introduction(Page):
    def vars_for_template(self):
        roles = {
            1: 'Brewery',
            2: 'Distributor',
            3: 'Wholesaler',
            4: 'Retailer'
        }
        return {
            'role': roles[self.id_in_group]
        }


class OrderPage(Page):
    form_model = 'player'
    form_fields = ['order_amount']

    # def before_next_page(self, timeout_happened=False):
        # for player in self.group.get_players(): 
            # if isinstance(player.order_amount, int) and 0 < player.order_amount < 10000:
                # self.group.update_order_amounts()
                # self.group.update_inventories()
                # player.calculate_inventory()

class ResultsWaitPage(WaitPage):
    def after_all_players_arrive(self):
        for player in self.group.get_players(): 
            if isinstance(player.order_amount, int) and 0 < player.order_amount < 10000:
                self.group.update_order_amounts()
                self.group.update_inventories()
                player.calculate_inventory()


class Results(Page):
    pass


page_sequence = [Introduction, OrderPage, ResultsWaitPage, Results]
