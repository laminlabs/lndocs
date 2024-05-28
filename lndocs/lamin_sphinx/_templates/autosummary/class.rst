{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :show-inheritance:

   {% block methods %}

   Methods
   -------

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

   {% endblock %}
