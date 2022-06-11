{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :show-inheritance:

   {% block attributes %}

   .. this is really just to see whether we'd print something
   {% set count = [] %}
   {% for item in attributes %}
   {% if item not in inherited_members %}
     {% set __ = count.append(1) %}
   {% endif %}
   {%- endfor %}

   {% if count %}
   .. rubric:: {{ _('Attributes') }}

   {% for item in attributes %}
   {% if item not in inherited_members %}
   .. autoattribute:: {{ item }}
   {% endif %}
   {%- endfor %}
   {% endif %}

   {% endblock %}

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
   {% if item not in inherited_members %}
   .. automethod:: {{ item }}
   {% endif %}
   {% endif %}
   {%- endfor %}
   {% endif %}

   {% endblock %}
