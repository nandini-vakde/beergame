from otree.api import *


doc = """
Your app description
"""

class C(BaseConstants):
    NAME_IN_URL = 'BeerGame'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 10
    ROLES = ['Brewery', 'Distributor', 'Wholesaler', 'Retailer']


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
        else:
            subsession.group_like_round(1)

class Group(BaseGroup):
    brewery_inventories = models.LongStringField(initial='[]')
    distributor_inventories = models.LongStringField(initial='[]')
    wholesaler_inventories = models.LongStringField(initial='[]')
    retailer_inventories = models.LongStringField(initial='[]')

    brewery_order_amounts = models.LongStringField(initial='[]')
    distributor_order_amounts = models.LongStringField(initial='[]')
    wholesaler_order_amounts = models.LongStringField(initial='[]')
    retailer_order_amounts = models.LongStringField(initial='[]')

    def update_order_amounts(self):
        for player in self.get_players():
            if player.game_role == 'Brewery':
                brewery_order_amounts.append(player.order_amounts)
            elif player.game_role == 'Distributor':
                distributor_order_amounts.append(player.order_amounts)
            elif player.game_role == 'Wholesaler':
                wholesaler_order_amounts.append(player.order_amounts)
            elif player.game_role == 'Retailer':
                retailer_order_amounts.append(player.order_amounts)
    
    def update_inventories(self):
        for player in self.get_players():
            if player.game_role == 'Brewery':
                brewery_inventories.append(player.inventory)
            elif player.game_role == 'Distributor':
                distributor_inventories.append(player.inventory)
            elif player.game_role == 'Wholesaler':
                wholesaler_inventories.append(player.inventory)
            elif player.game_role == 'Retailer':
                retailer_inventories.append(player.inventory)


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

    def calculate_inventory(self):
        # still need to calculate in transit, demand, and backorder
        for player in self.get_players():
            if player.game_role == 'Brewery':
                if len(distributor_order_amounts) >= self.group.subsession.round_number - 1:
                    self.inventory = max(0, self.inventory - distributor_order_amounts[self.group.subsession.round_number - 2])
            elif player.game_role == 'Distributor':
                if len(wholesaler_order_amounts) >= self.group.subsession.round_number - 1:
                    self.inventory = max(0, self.inventory - wholesaler_order_amounts[self.group.subsession.round_number - 2])
            elif player.game_role == 'Wholesaler':
                if len(retailer_order_amounts) >= self.group.subsession.round_number - 1:
                    self.inventory = max(0, self.inventory - retailer_order_amounts[self.group.subsession.round_number - 2])
            elif player.game_role == 'Retailer':
                retailer_order_amounts.append(player.order_amounts)
        # Simplified inventory logic
        self.inventory = max(0, self.inventory - self.order_amount) # Adjust for real logic
        self.backorder = max(0, self.order_amount - self.inventory) # Adjust for real logic


class Introduction(Page):
    def vars_for_template(self):
        return {
            'role': self.player.game_role
        }

class OrderPage(Page):
    form_model = 'player'
    form_fields = ['order_amount']

    def before_next_page(self):
        for player in self.get_players():
            if isinstance(self.player.order_amount, int) and 0 < self.order_amount < 10000:
                self.group.update_order_amounts()
                self.player.calculate_inventory()
            # else ask again?

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = 'set_payoffs'

class Results(Page):
    pass

page_sequence = [Introduction, OrderPage, ResultsWaitPage, Results]