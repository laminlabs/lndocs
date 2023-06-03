{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :show-inheritance:

   {% block methods %}

   .. this is really just to see whether we'd print something
   {% set count = [] %}
   {% for item in methods %}
   {% if '__init__' not in item %}
   {% if item not in inherited_members %}
     {% set __ = count.append(1) %}
   {% endif %}
   {% endif %}
   {%- endfor %}

   .. now, actually print
   {% if count %}
   .. rubric:: {{ _('Methods') }}

   {% for item in methods %}
   {% if '__init__' not in item %}
   {% if 'get_next_' not in item %}
   {% if 'get_previous_' not in item %}
   {% if item not in inherited_members %}
   .. automethod:: {{ item }}
   {% endif %}
   {% endif %}
   {% endif %}
   {% endif %}
   {%- endfor %}
   {% endif %}

   {% endblock %}
