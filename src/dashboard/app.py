import sys
import os
import pickle

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path
import time
from typing import Dict, List, Set, Optional
import threading
from src.core.ticket_management import TicketManager, Ticket, Priority, Status
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

class Dashboard:
    def __init__(self):
        self.ticket_manager = TicketManager()
        self.data_dir = Path("dashboard_data")
        self.data_dir.mkdir(exist_ok=True)
        self.known_tickets_file = self.data_dir / "known_tickets.pkl"
        self.recent_activity_file = self.data_dir / "recent_activity.pkl"
        
        # Initialize session state
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now() - timedelta(minutes=5)  # Check last 5 minutes initially
        
        # Load known tickets from file if exists
        if 'known_tickets' not in st.session_state:
            st.session_state.known_tickets = self.load_known_tickets()
            
        # Load recent activity from file if exists
        if 'recent_activity' not in st.session_state:
            st.session_state.recent_activity = self.load_recent_activity()
            
        # Initialize selected ticket
        if 'selected_ticket' not in st.session_state:
            st.session_state.selected_ticket = None
            
        self.update_interval = 5  # seconds

    def load_known_tickets(self) -> Set[str]:
        """Load known tickets from disk."""
        try:
            if self.known_tickets_file.exists():
                with open(self.known_tickets_file, 'rb') as f:
                    return pickle.load(f)
            return set()
        except Exception as e:
            st.error("Error loading known tickets: {}".format(str(e)))
            return set()

    def save_known_tickets(self, known_tickets: Set[str]) -> None:
        """Save known tickets to disk."""
        try:
            with open(self.known_tickets_file, 'wb') as f:
                pickle.dump(known_tickets, f)
        except Exception as e:
            st.error("Error saving known tickets: {}".format(str(e)))
            
    def load_recent_activity(self) -> List[Dict]:
        """Load recent activity from disk."""
        try:
            if self.recent_activity_file.exists():
                with open(self.recent_activity_file, 'rb') as f:
                    return pickle.load(f)
            return []
        except Exception as e:
            st.error("Error loading recent activity: {}".format(str(e)))
            return []

    def save_recent_activity(self, recent_activity: List[Dict]) -> None:
        """Save recent activity to disk."""
        try:
            with open(self.recent_activity_file, 'wb') as f:
                pickle.dump(recent_activity, f)
        except Exception as e:
            st.error("Error saving recent activity: {}".format(str(e)))

    def get_tickets_dataframe(self) -> pd.DataFrame:
        """Convert tickets to a pandas DataFrame for display."""
        tickets = self.ticket_manager.get_all_tickets()
        data = []
        
        for ticket in tickets.values():
            data.append({
                'Ticket ID': ticket.ticket_id,
                'Type': ticket.ticket_type.value,
                'Priority': ticket.priority.value,
                'Status': ticket.status.value,
                'Submitted At': ticket.date_submitted.strftime('%Y-%m-%d %H:%M:%S'),
                'Resolved At': ticket.date_resolved.strftime('%Y-%m-%d %H:%M:%S') if ticket.date_resolved else 'N/A',
                'Description': ticket.description[:100] + '...' if len(ticket.description) > 100 else ticket.description,
                'User': ticket.submitted_by.name,
                'Location': ticket.submitted_by.location
            })
        
        return pd.DataFrame(data)

    def select_ticket(self, ticket_id):
        """Callback for ticket selection."""
        st.session_state.selected_ticket = ticket_id
        st.rerun()

    def show_ticket_details(self, ticket_id: str) -> None:
        """Show detailed ticket information in a modal."""
        ticket = self.ticket_manager.get_ticket(ticket_id)
        if not ticket:
            st.error("Ticket {} not found".format(ticket_id))
            return

        # Create a modal for ticket details
        with st.expander("Ticket Details", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Basic Information")
                st.write("**Ticket ID:** {}".format(ticket.ticket_id))
                st.write("**Type:** {}".format(ticket.ticket_type.value))
                st.write("**Priority:** {}".format(ticket.priority.value))
                st.write("**Status:** {}".format(ticket.status.value))
                st.write("**Submitted At:** {}".format(ticket.date_submitted.strftime('%Y-%m-%d %H:%M:%S')))
                if ticket.date_resolved:
                    st.write("**Resolved At:** {}".format(ticket.date_resolved.strftime('%Y-%m-%d %H:%M:%S')))
                
                st.subheader("User Information")
                st.write("**Name:** {}".format(ticket.submitted_by.name))
                st.write("**Email:** {}".format(ticket.submitted_by.email))
                st.write("**Location:** {}".format(ticket.submitted_by.location))
            
            with col2:
                st.subheader("Description")
                st.write(ticket.description)
                
                if ticket.subcategories:
                    st.subheader("Subcategories")
                    for subcat in ticket.subcategories:
                        confidence = float(subcat['confidence'])
                        confidence_str = "{:.2f}".format(confidence)
                        category = str(subcat['category'])
                        st.write("- " + category + ": " + confidence_str)
                
                if ticket.assigned_to:
                    st.subheader("Assignment")
                    st.write("**Assigned To:** {}".format(ticket.assigned_to.name))
                    st.write("**Team:** {}".format(ticket.assigned_to.team))
                
                if ticket.resolution_notes:
                    st.subheader("Resolution Notes")
                    st.write(ticket.resolution_notes)
                
                if ticket.notes:
                    st.subheader("Additional Notes")
                    for note in ticket.notes:
                        st.write("- {}".format(note))

    def check_for_new_tickets(self) -> List[Dict]:
        """Check for new tickets since last update."""
        new_tickets = []
        tickets = self.ticket_manager.get_all_tickets()
        
        # Get current ticket IDs
        current_ticket_ids = set(tickets.keys())
        
        # Find new tickets (not in known_tickets)
        new_ticket_ids = current_ticket_ids - st.session_state.known_tickets
        
        for ticket_id in new_ticket_ids:
            ticket = tickets[ticket_id]
            new_tickets.append({
                'id': ticket.ticket_id,
                'type': ticket.ticket_type.value,
                'priority': ticket.priority.value,
                'description': ticket.description[:100] + '...' if len(ticket.description) > 100 else ticket.description,
                'submitted_at': ticket.date_submitted.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Update known tickets
        st.session_state.known_tickets = current_ticket_ids
        # Save known tickets to file for persistence between runs
        self.save_known_tickets(current_ticket_ids)
        st.session_state.last_update = datetime.now()
        
        # If we found new tickets, update the recent activity
        if new_tickets:
            st.session_state.recent_activity = new_tickets
            self.save_recent_activity(new_tickets)
        
        return new_tickets

    def run(self):
        st.set_page_config(
            page_title="HelpDesk Ticket Dashboard",
            page_icon="🎫",
            layout="wide"
        )

        st.title("HelpDesk Ticket Dashboard")
        
        # Sidebar for filters
        st.sidebar.header("Filters")
        
        # Date range filter
        st.sidebar.subheader("Date Filter")
        
        # Get min and max dates from tickets
        df = self.get_tickets_dataframe()
        if not df.empty:
            # Convert string dates to datetime objects
            df['Submitted At'] = pd.to_datetime(df['Submitted At'])
            min_date = df['Submitted At'].min().date()
            max_date = df['Submitted At'].max().date()
            
            # Set default to last 7 days or full range if shorter
            default_start = max(min_date, (datetime.now() - timedelta(days=7)).date())
            
            # Date inputs
            start_date = st.sidebar.date_input(
                "From", 
                value=default_start,
                min_value=min_date,
                max_value=max_date
            )
            
            end_date = st.sidebar.date_input(
                "To",
                value=max_date,
                min_value=min_date,
                max_value=max_date
            )
            
            # Add a separator
            st.sidebar.markdown("---")
        
        st.sidebar.subheader("Category Filters")
        ticket_type = st.sidebar.multiselect(
            "Ticket Type",
            options=["Incident", "Demande"],
            default=["Incident", "Demande"]
        )
        
        priority = st.sidebar.multiselect(
            "Priority",
            options=[p.value for p in Priority],
            default=[p.value for p in Priority]
        )
        
        status = st.sidebar.multiselect(
            "Status",
            options=[s.value for s in Status],
            default=[s.value for s in Status]
        )

        # Reset notifications button
        st.sidebar.markdown("---")
        st.sidebar.subheader("Actions")
        if st.sidebar.button("Reset Notifications"):
            st.session_state.known_tickets = set()
            st.session_state.recent_activity = []
            self.save_known_tickets(set())
            self.save_recent_activity([])
            st.rerun()

        # Add a refresh button
        if st.sidebar.button("Refresh Dashboard"):
            st.rerun()

        # Create main layout with two columns
        left_col, right_col = st.columns([3, 1])
        
        # Right column - Recent Activity
        with right_col:
            st.subheader("Recent Activity")
            
            # Check for new tickets
            new_tickets = self.check_for_new_tickets()
            
            # Only update the recent activity if there are new tickets
            if new_tickets:
                show_tickets = new_tickets
            else:
                show_tickets = st.session_state.recent_activity
            
            if show_tickets:
                for ticket in show_tickets:
                    with st.container():
                        st.info("""
                        **Recent Ticket Activity**
                        - ID: {id}
                        - Type: {type}
                        - Priority: {priority}
                        - Submitted: {submitted_at}
                        - Description: {description}
                        """.format(
                            id=ticket['id'],
                            type=ticket['type'],
                            priority=ticket['priority'],
                            submitted_at=ticket['submitted_at'],
                            description=ticket['description']
                        ))
            else:
                st.info("No recent ticket activity")
                
            # Show last update time
            st.caption("Last updated: {}".format(st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')))
            st.caption("Tracking {} tickets".format(len(st.session_state.known_tickets)))
            
        # Left column - Ticket History and Details
        with left_col:
            st.subheader("Ticket History")
            df = self.get_tickets_dataframe()
            
            # Apply date filter if we have tickets and the date filter has been set
            if not df.empty and 'start_date' in locals() and 'end_date' in locals():
                # Convert string dates to datetime for filtering
                df['Submitted At'] = pd.to_datetime(df['Submitted At'])
                
                # Filter by date range
                df = df[(df['Submitted At'].dt.date >= start_date) & 
                         (df['Submitted At'].dt.date <= end_date)]
            
            # Apply other filters
            if ticket_type:
                df = df[df['Type'].isin(ticket_type)]
            if priority:
                df = df[df['Priority'].isin(priority)]
            if status:
                df = df[df['Status'].isin(status)]
            
            # Add active filters information
            if not df.empty and 'start_date' in locals() and 'end_date' in locals():
                if start_date != min_date or end_date != max_date:
                    st.caption("Filtered by date: {} to {}".format(
                        start_date.strftime('%Y-%m-%d'), 
                        end_date.strftime('%Y-%m-%d')
                    ))
            
            # Sort tickets by submission date (newest first)
            if not df.empty:
                # Make sure 'Submitted At' is datetime for proper sorting
                if not pd.api.types.is_datetime64_dtype(df['Submitted At']):
                    df['Submitted At'] = pd.to_datetime(df['Submitted At'])
                
                # Sort by submission date in descending order
                df = df.sort_values(by='Submitted At', ascending=False)
                
                # Convert back to string for display if needed
                if not pd.api.types.is_datetime64_dtype(df['Submitted At']):
                    df['Submitted At'] = df['Submitted At'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Add a helper message
            st.info("Select a row from the table to view ticket details")
            
            # Display ticket table
            if not df.empty:
                # Display standard dataframe without on_click
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Create a selection mechanism
                ticket_options = {row["Ticket ID"]: "{}: {} - {}".format(
                    row['Ticket ID'], row['Type'], row['Priority']) 
                    for _, row in df.iterrows()}
                
                # Add a select box for ticket selection
                selected_ticket = st.selectbox(
                    "Select a ticket to view details:",
                    options=list(ticket_options.keys()),
                    format_func=lambda x: ticket_options[x],
                    key="ticket_selector"
                )
                
                if selected_ticket:
                    st.session_state.selected_ticket = selected_ticket
            else:
                st.info("No tickets found matching the current filters.")
            
            # Show ticket details if a ticket is selected
            if st.session_state.selected_ticket:
                ticket_id = st.session_state.selected_ticket
                ticket = self.ticket_manager.get_ticket(ticket_id)
                
                if ticket:
                    # Create a modal-like container for ticket details
                    with st.container():
                        # Create a header with a close button
                        detail_header_col1, detail_header_col2 = st.columns([5, 1])
                        
                        with detail_header_col1:
                            st.subheader("Ticket Details: {}".format(ticket_id))
                        
                        with detail_header_col2:
                            if st.button("Close", key="close_details_{}".format(ticket_id)):
                                st.session_state.selected_ticket = None
                                st.rerun()
                        
                        # Create a colored container based on priority
                        priority_colors = {
                            "Low": "blue",
                            "Medium": "orange",
                            "High": "red",
                            "Critical": "darkred"
                        }
                        
                        priority_color = priority_colors.get(ticket.priority.value, "gray")
                        
                        st.markdown("""
                        <div style="padding: 10px; border-radius: 5px; border-left: 5px solid {color}; background-color: rgba(0,0,0,0.05);">
                        """.format(color=priority_color), unsafe_allow_html=True)
                        
                        details_col1, details_col2 = st.columns(2)
                        
                        with details_col1:
                            st.markdown("#### Basic Information")
                            st.write("**Ticket ID:** {}".format(ticket.ticket_id))
                            st.write("**Type:** {}".format(ticket.ticket_type.value))
                            st.write("**Priority:** {}".format(ticket.priority.value))
                            st.write("**Status:** {}".format(ticket.status.value))
                            st.write("**Submitted At:** {}".format(ticket.date_submitted.strftime('%Y-%m-%d %H:%M:%S')))
                            if ticket.date_resolved:
                                st.write("**Resolved At:** {}".format(ticket.date_resolved.strftime('%Y-%m-%d %H:%M:%S')))
                            
                            st.markdown("#### User Information")
                            st.write("**Name:** {}".format(ticket.submitted_by.name))
                            st.write("**Email:** {}".format(ticket.submitted_by.email))
                            st.write("**Location:** {}".format(ticket.submitted_by.location))
                        
                        with details_col2:
                            st.markdown("#### Description")
                            st.write(ticket.description)
                            
                            if ticket.subcategories:
                                st.markdown("#### Subcategory")
                                for subcat in ticket.subcategories:
                                    category = str(subcat['subcategory'])
                                    st.write("- " + category)
                            
                            if ticket.assigned_to:
                                st.markdown("#### Assignment")
                                st.write("**Assigned To:** {}".format(ticket.assigned_to.name))
                                st.write("**Team:** {}".format(ticket.assigned_to.team))
                            
                            if ticket.resolution_notes:
                                st.markdown("#### Resolution Notes")
                                st.write(ticket.resolution_notes)
                            
                            if ticket.notes:
                                st.markdown("#### Additional Notes")
                                for note in ticket.notes:
                                    st.write("- {}".format(note))
                        
                        st.markdown("</div>", unsafe_allow_html=True)

        # Auto-refresh using st.rerun()
        time.sleep(self.update_interval)
        st.rerun()

if __name__ == "__main__":
    dashboard = Dashboard()
    dashboard.run() 