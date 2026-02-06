from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .choices import CircuitTerminationSideChoices
from .models import CircuitTermination


@receiver(post_save, sender=CircuitTermination)
def update_circuit(instance, raw=False, **kwargs):
    """
    When a CircuitTermination has been modified, update its parent Circuit.
    """
    if raw:
        return
    if instance.term_side in CircuitTerminationSideChoices.values():
        termination_name = f"circuit_termination_{instance.term_side.lower()}"
        setattr(instance.circuit, termination_name, instance)
        setattr(instance.circuit, "last_updated", timezone.now())
        instance.circuit.save()
