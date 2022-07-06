import sys
import os
import argparse
from collections import namedtuple
import pickle as pk
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable
from torch.distributions import Categorical
import copy

import model_utilities
import numpy as np

class MetaDiscriminator(nn.Module):
    def __init__(self, args, kg, metapath_hidden_sizes):
        super(MetaDiscriminator, self).__init__()

        self.args = args
        self.entity_type_embeds = nn.Embedding(kg.num_entity_types, args.entity_type_dim)
        nn.init.xavier_normal_(self.entity_type_embeds.weight)

        self.metapath_hidden_sizes = metapath_hidden_sizes
        input_shape = (args.max_path + 1 - 1) * self.entity_type_embeds.weight.shape[1]
        self.model = torch.nn.Sequential(
            torch.nn.Linear(input_shape, self.metapath_hidden_sizes[0]),
            nn.BatchNorm1d(metapath_hidden_sizes[0]),
            nn.ELU(),
            nn.Dropout(p=self.args.metadisc_dropout_rate),
            torch.nn.Linear(self.metapath_hidden_sizes[0], self.metapath_hidden_sizes[1]),
            nn.BatchNorm1d(self.metapath_hidden_sizes[1]),
            nn.ELU(),
            nn.Dropout(p=self.args.metadisc_dropout_rate),
            torch.nn.Linear(self.metapath_hidden_sizes[1], 1)
        )

    def get_metapath_embedding(self, metapaths):
        metapath_embedding = self.entity_type_embeds(metapaths).view(metapaths.shape[0],-1)
        return metapath_embedding

    def forward(self, metapaths):
        emb = self.get_metapath_embedding(metapaths)
        logit = self.model(emb)
        return logit

    def get_reward(self, metapaths):
        generator_logit = self.forward(metapaths)
        s = torch.sigmoid(generator_logit)
        discriminator_reward = torch.log(s+1e-8) - torch.log(1-s+1e-8)
        return discriminator_reward.detach()


class Discriminator(nn.Module):
    def __init__(self, args, kg, state_emb_dim, disc_hidden_sizes):
        super(Discriminator, self).__init__()

        self.args = args
        self.kg = kg

        self.relation_embeds = nn.Embedding(kg.relation_embeddings.weight.shape[0], kg.relation_embeddings.weight.shape[1], padding_idx=0)
        self.entity_embeds = nn.Embedding(kg.entity_embeddings.weight.shape[0], kg.entity_embeddings.weight.shape[1], padding_idx=0)
        nn.init.xavier_normal_(self.relation_embeds.weight)
        nn.init.xavier_normal_(self.entity_embeds.weight)

        self.disc_hidden_sizes = disc_hidden_sizes
        input_shape = state_emb_dim + self.relation_embeds.weight.shape[1] + self.entity_embeds.weight.shape[1]
        self.model = torch.nn.Sequential(
            torch.nn.Linear(input_shape, self.disc_hidden_sizes[0]),
            nn.BatchNorm1d(self.disc_hidden_sizes[0]),
            nn.ELU(),
            nn.Dropout(p=self.args.disc_dropout_rate),
            torch.nn.Linear(self.disc_hidden_sizes[0], self.disc_hidden_sizes[1]),
            nn.BatchNorm1d(self.disc_hidden_sizes[1]),
            nn.ELU(),
            nn.Dropout(p=self.args.disc_dropout_rate),
            torch.nn.Linear(self.disc_hidden_sizes[1], 1)
        )

    def get_action_embedding(self, action):
        r, e = action
        relation_embedding = self.relation_embeds(r)
        entity_embedding = self.entity_embeds(e)
        action_embedding = torch.cat([relation_embedding, entity_embedding], dim=-1)
        return action_embedding

    def forward(self, state_input, action):
        # Embedding
        state_emb = self.kg.entity_embeddings(state_input[:,:2]).view(state_input.shape[0],-1)
        for index in range(2,state_input.shape[1],2):
            temp_e_state_emb = self.kg.entity_embeddings(state_input[:,index]).view(state_input.shape[0],-1)
            temp_r_state_emb = self.kg.relation_embeddings(state_input[:,index+1]).view(state_input.shape[0],-1)
            state_emb = torch.cat([state_emb,temp_e_state_emb,temp_r_state_emb],dim=1)

        action_emb = self.get_action_embedding(action)
        iuput_x = torch.cat([state_emb, action_emb], 1)
        logit = self.model(iuput_x)
        return logit

    def get_reward(self, state_input, action):
        generator_logit = self.forward(state_input, action)
        s = torch.sigmoid(generator_logit)
        discriminator_reward = torch.log(s + 1e-8) - torch.log(1 - s + 1e-8)
        return discriminator_reward.detach()


class Net(nn.Module):
    def __init__(self, args, kg, state_emb_dim, hidden_sizes, entity_init_size=100):
        super(Net, self).__init__()

        self.args = args
        self.kg = kg

        out_dim = self.kg.relation_embeddings.weight.shape[1] + self.kg.entity_embeddings.weight.shape[1]
        self.actor_ls = nn.Sequential(
            nn.Linear(state_emb_dim, hidden_sizes[0]),
            nn.BatchNorm1d(hidden_sizes[0]),
            nn.ELU(),
            nn.Dropout(p=self.args.actor_dropout_rate),
            nn.Linear(hidden_sizes[0], hidden_sizes[1]),
            nn.BatchNorm1d(hidden_sizes[1]),
            nn.ELU(),
            nn.Dropout(p=self.args.actor_dropout_rate),
            nn.Linear(hidden_sizes[1], out_dim)
        ) 

        self.critic_ls = nn.Sequential(
            nn.Linear(state_emb_dim, hidden_sizes[0]),
            nn.BatchNorm1d(hidden_sizes[0]),
            nn.ELU(),
            nn.Dropout(p=self.args.critic_dropout_rate),
            nn.Linear(hidden_sizes[0], hidden_sizes[1]),
            nn.BatchNorm1d(hidden_sizes[1]),
            nn.ELU(),
            nn.Dropout(p=self.args.critic_dropout_rate),
            nn.Linear(hidden_sizes[1], out_dim)
        ) 

        self.actor_r = nn.Embedding(kg.relation_embeddings.weight.shape[0], kg.relation_embeddings.weight.shape[1], padding_idx=0)
        self.actor_e = nn.Embedding(kg.entity_embeddings.weight.shape[0], kg.entity_embeddings.weight.shape[1], padding_idx=0)
        self.critic_r = nn.Embedding(kg.relation_embeddings.weight.shape[0], kg.relation_embeddings.weight.shape[1], padding_idx=0)
        self.critic_e = nn.Embedding(kg.entity_embeddings.weight.shape[0], kg.entity_embeddings.weight.shape[1], padding_idx=0)
        nn.init.xavier_normal_(self.actor_r.weight)
        nn.init.xavier_normal_(self.actor_e.weight)
        nn.init.xavier_normal_(self.critic_r.weight)
        nn.init.xavier_normal_(self.critic_e.weight)

    def get_action_embedding(self, action, type='actor'):
        r, e = action
        if type == 'actor':
            relation_embedding = self.actor_r(r)
            entity_embedding = self.actor_e(e)
        else:
            relation_embedding = self.critic_r(r)
            entity_embedding = self.critic_e(e)
        action_embedding = torch.cat([relation_embedding, entity_embedding], dim=-1)
        return action_embedding

    def forward(self, state_input, action_space):
        # Embedding
        state_emb = self.kg.entity_embeddings(state_input[:,:2]).view(state_input.shape[0],-1)
        for index in range(2,state_input.shape[1],2):
            temp_e_state_emb = self.kg.entity_embeddings(state_input[:,index]).view(state_input.shape[0],-1)
            temp_r_state_emb = self.kg.relation_embeddings(state_input[:,index+1]).view(state_input.shape[0],-1)
            state_emb = torch.cat([state_emb,temp_e_state_emb,temp_r_state_emb],dim=1)

        (r_space, e_space), action_mask = action_space
        action_mask = action_mask == 1

        # Actor
        actor_out = self.actor_ls(state_emb)
        sparse_actor = self.get_action_embedding((r_space, e_space), 'actor')
        actor_logits = torch.bmm(sparse_actor, actor_out.unsqueeze(-1)).squeeze(-1)        
        actor_logits[~action_mask] = -float('inf')
        act_probs = F.softmax(actor_logits, dim=-1)

        # Critic
        critic_out = self.critic_ls(state_emb)
        sparse_critic = self.get_action_embedding((r_space, e_space), 'critic')
        q_actions = torch.bmm(sparse_critic, critic_out.unsqueeze(-1)).squeeze(-1)        

        return act_probs, q_actions

class ActorCritic(object):
    def __init__(self, args, kg, history_len, gamma=0.99, target_update=0.05, hidden_sizes=(512, 512), step_up_target_net=True):

        self.args = args
        self.kg = kg

        self.history_len = history_len

        self.state_emb_dim = self.kg.entity_embeddings.weight.shape[1] * 2 + self.history_len * (self.kg.entity_embeddings.weight.shape[1] + self.kg.relation_embeddings.weight.shape[1])
        self.gamma = args.gamma

        self.target_update = target_update

        self.policy_net = Net(self.args, self.kg, self.state_emb_dim, hidden_sizes).to(args.device)
        if step_up_target_net:
            self.target_net = Net(self.args, self.kg, self.state_emb_dim, hidden_sizes).requires_grad_(False).to(args.device)
            self.target_net.load_state_dict(self.policy_net.state_dict())
            self.target_net.eval()
        else:
            self.target_net = None

        self.get_reward = None

    @staticmethod
    def process_state(history_len, batch_state):
        sids = batch_state[0].view(-1,1)
        curr_node_ids = batch_state[2][:,-1].view(-1,1)
        node_history = batch_state[2][:,:-1]
        history_path_len = node_history.shape[1]

        pad_idx = 0
        state_input = torch.cat([sids,curr_node_ids],dim=1)
        for hid in range(history_len):
            if hid <= history_path_len - 1:
                colidx = history_path_len - 1 - hid
                pre_nodes = batch_state[2][:,colidx].view(-1,1)
                pre_relations = batch_state[1][:,colidx+1].view(-1,1)
            else:
                pre_nodes = torch.tensor([pad_idx] * len(sids)).view(-1,1)
                pre_relations = torch.tensor([pad_idx] * len(sids)).view(-1,1)
            state_input = torch.cat([state_input,pre_nodes,pre_relations],dim=1)

        return state_input

    @staticmethod
    def apply_action_dropout_probs(probs, dropout):
        if dropout > 0:
            copy_probs = copy.deepcopy(probs.detach())
            for row in copy_probs:
                one_index = torch.where(row!=0)[0]
                one_index = one_index[torch.randperm(len(one_index))]
                num_zeros = int(len(one_index)*dropout)
                row[one_index[:num_zeros]] = 0
            return copy_probs
        else:
            return probs

    def select_action(self, state_inputs, action_spaces, device, act_dropout):
        state_inputs = state_inputs.to(device)
        ((r_space, e_space), action_mask) = action_spaces
        action_spaces = ((r_space, e_space), action_mask)

        probs, q_actions = self.policy_net(state_inputs, action_spaces)
        copy_probs = self.apply_action_dropout_probs(probs, act_dropout)

        try:
            acts_idx = Categorical(copy_probs).sample()
        except ValueError: ## to avoid a strange error: ValueError: Expected parameter probs (Tensor of shape (1120, 3050)) of distribution Categorical(probs: torch.Size([1120, 3050])) to satisfy the constraint Simplex(), but found invalid values:
            try:
                acts_idx = torch.hstack([Categorical(x).sample() for x in copy_probs])
            except:
                with open('check.pkl','wb') as outfile:
                    pk.dump([probs,copy_probs],outfile)
                    exit()

        m2 = Categorical(probs)

        q_act = q_actions.gather(1, acts_idx.view(-1, 1)).view(-1)

        saved_output = SavedOutput(probs, q_actions, m2.log_prob(acts_idx), q_act, m2.entropy())

        acts_idx = acts_idx.to(device)
        sample_r_action = r_space.gather(1, acts_idx.view(-1, 1)).view(-1)
        sample_e_action = e_space.gather(1, acts_idx.view(-1, 1)).view(-1)

        return (sample_r_action, sample_e_action), saved_output

    def update_target_net_(self):
        policy_dict = self.policy_net.state_dict()
        target_dict = self.target_net.state_dict()
        for para in target_dict:
            target_dict[para] = self.target_update * policy_dict[para] + (1-self.target_update) * target_dict[para]
        self.target_net.load_state_dict(target_dict)


class DiscriminatorActorCritic(ActorCritic):
    def __init__(self, args, kg, history_len, gamma=0.99, target_update=0.05,
                 ac_hidden_sizes=(512, 256), discriminator_hidden_sizes=(512, 512), metadiscriminator_hidden_sizes=(512, 256)):
        super(DiscriminatorActorCritic, self).__init__(args, kg, history_len, gamma, target_update, ac_hidden_sizes, False)

        self.discriminator = Discriminator(
            args=self.args, 
            kg=self.kg,
            state_emb_dim=self.state_emb_dim,
            disc_hidden_sizes=discriminator_hidden_sizes
        ).to(args.device)
        self.metadiscriminator = MetaDiscriminator(
            args=self.args,
            kg=self.kg,
            metapath_hidden_sizes=metadiscriminator_hidden_sizes
        ).to(args.device)

        self.get_reward = self.discriminator.get_reward
        self.get_reward_meta = self.metadiscriminator.get_reward

    def step_update_discriminator(self, expert_batch, train_batch, label, optimizer, device):
        state_input = train_batch.state.to(device)
        action = [action.to(device) for action in train_batch.action]

        expert_state_input = expert_batch.state.to(device)
        expert_action = [action.to(device) for action in expert_batch.action]
        total_loss = 0.0

        label = torch.tensor(label).float().view(-1, 1).to(device)

        generator_logit = self.discriminator(state_input, action)
        expert_logit = self.discriminator(expert_state_input, expert_action)

        generator_loss = F.binary_cross_entropy_with_logits(generator_logit, label)
        expert_loss = F.binary_cross_entropy_with_logits(expert_logit, torch.ones_like(expert_logit))

        total_loss = generator_loss + expert_loss

        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

        return total_loss.item()

    def update_metadiscriminator(self, expert_metapath, metapath, label, optimizer, device):

        label = torch.tensor(label).float().view(-1, 1).to(device)
        expert_metapath = expert_metapath.to(device)
        metapath = metapath.to(device)

        total_loss = 0.0

        generator_logit = self.metadiscriminator(metapath)
        expert_logit = self.metadiscriminator(expert_metapath)

        generator_loss = F.binary_cross_entropy_with_logits(generator_logit, label)
        expert_loss = F.binary_cross_entropy_with_logits(expert_logit, torch.ones_like(expert_logit))

        total_loss = generator_loss + expert_loss

        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

        return total_loss.item()

    def step_update_with_expert(self, metapath, saved_output, train_batch, batch_reward, device, alpha=0.1, alpha_meta=0.1, last_step=False):

        if last_step is True:
            curr_reward = batch_reward
        else:
            if self.get_reward is not None:
                state_input = train_batch.state.to(device)
                action = [action.to(device) for action in train_batch.action]
                expert_reward = self.get_reward(state_input, action).to(device).view(-1)
            else:
                expert_reward = 0

            if self.get_reward_meta is not None:
                inputs = metapath.to(device)
                expert_reward_meta = self.get_reward_meta(inputs).to(device).view(-1)
            else:
                expert_reward_meta = 0

            gen_reward = batch_reward
            curr_reward = alpha * expert_reward + alpha_meta * expert_reward_meta + (1 - alpha - alpha_meta) * gen_reward

        log_prob = saved_output.log_prob_action
        value = saved_output.q_action
        advantage = curr_reward - value
        actor_loss = -log_prob * advantage.detach()
        critic_loss = advantage.pow(2)
        entropy_loss = -saved_output.entropy

        actor_loss = actor_loss.mean()
        critic_loss = critic_loss.mean()
        entropy_loss = entropy_loss.mean()

        # loss = actor_loss + critic_loss + ent_weight * entropy_loss

        return actor_loss, critic_loss, entropy_loss