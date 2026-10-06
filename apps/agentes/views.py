from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from apps.agentes.forms import AgenteForm
from apps.agentes.models import Agente
from apps.auditoria.services import Acao, registrar
from apps.core.permissoes import AdministradorMixin


class AgenteListView(AdministradorMixin, ListView):
    template_name = "agentes/lista.html"
    context_object_name = "agentes"
    queryset = Agente.objects.select_related("modelo__provedor")


class _AgenteFormMixin(AdministradorMixin):
    model = Agente
    form_class = AgenteForm
    template_name = "agentes/form.html"
    success_url = reverse_lazy("agentes:lista")
    verbo = ""

    def form_valid(self, form):
        resposta = super().form_valid(form)
        registrar(
            Acao.CADASTRO_AGENTE,
            request=self.request,
            agente=self.object.nome,
            provedor=self.object.modelo.provedor.tipo,
            modelo=self.object.modelo.identificador,
            objeto=f"Agente {self.verbo}",
        )
        messages.success(self.request, f"Agente {self.verbo}.")
        return resposta


class AgenteCreateView(_AgenteFormMixin, CreateView):
    verbo = "cadastrado"


class AgenteUpdateView(_AgenteFormMixin, UpdateView):
    verbo = "alterado"
