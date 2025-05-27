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
from src.core.ticket_management import TicketManager

class Dashboard:
    def __init__(self):
        self.ticket_manager = TicketManager()
        # Remove file-based logic: no data_dir, known_tickets_file, recent_activity_file
        # Initialize session state
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now() - timedelta(minutes=5)
        if 'known_tickets' not in st.session_state:
            st.session_state.known_tickets = set()
        if 'recent_activity' not in st.session_state:
            st.session_state.recent_activity = []
        if 'selected_ticket' not in st.session_state:
            st.session_state.selected_ticket = None
        self.update_interval = 5  # seconds

    def get_tickets_dataframe(self) -> pd.DataFrame:
        tickets = self.ticket_manager.get_all_tickets()
        data = []
        for ticket_id, ticket_data in tickets.items():
            if hasattr(ticket_data, 'to_dict'):
                ticket = ticket_data
                user_name = ticket.user.get('name', 'Unknown') if isinstance(ticket.user, dict) else 'Unknown'
                user_location = ticket.user.get('location', '') if isinstance(ticket.user, dict) else ''
                final_subcategory = ticket.final_subcategory if hasattr(ticket, 'final_subcategory') else ""
                affectation_team = ticket.affectation_team if hasattr(ticket, 'affectation_team') else ""
                is_temp = ticket.is_temp if hasattr(ticket, 'is_temp') else False
                temp_stage = ticket.stage if hasattr(ticket, 'stage') and is_temp else ""
                data.append({
                    'Ticket ID': ticket.ticket_id,
                    'Type': ticket.ticket_type,
                    'Priority': ticket.priority,
                    'Status': ticket.status,
                    'Temp Status': f"TEMP ({temp_stage})" if is_temp else "",
                    'Subcategory': final_subcategory,
                    'Affectation Team': affectation_team,
                    'Submitted At': ticket.date_submitted.strftime('%Y-%m-%d %H:%M:%S') if hasattr(ticket.date_submitted, 'strftime') else ticket.date_submitted,
                    'Resolved At': ticket.date_resolved.strftime('%Y-%m-%d %H:%M:%S') if ticket.date_resolved and hasattr(ticket.date_resolved, 'strftime') else 'N/A',
                    'Description': ticket.description[:100] + '...' if len(ticket.description) > 100 else ticket.description,
                    'User': user_name,
                    'Location': user_location,
                    'Thread ID': ticket.thread_id or ''
                })
            else:
                user = ticket_data.get('user', {})
                user_name = user.get('name', 'Unknown') if isinstance(user, dict) else 'Unknown'
                user_location = user.get('location', '') if isinstance(user, dict) else ''
                final_subcategory = ticket_data.get('final_subcategory', "")
                affectation_team = ticket_data.get('affectation_team', "")
                is_temp = ticket_data.get('is_temp', False)
                temp_stage = ticket_data.get('stage', "") if is_temp else ""
                date_submitted = ticket_data.get('date_submitted')
                if isinstance(date_submitted, str):
                    date_str = date_submitted
                elif hasattr(date_submitted, 'strftime'):
                    date_str = date_submitted.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    date_str = str(date_submitted)
                date_resolved = ticket_data.get('date_resolved')
                if date_resolved:
                    if isinstance(date_resolved, str):
                        resolved_str = date_resolved
                    elif hasattr(date_resolved, 'strftime'):
                        resolved_str = date_resolved.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        resolved_str = str(date_resolved)
                else:
                    resolved_str = 'N/A'
                data.append({
                    'Ticket ID': ticket_id,
                    'Type': ticket_data.get('ticket_type', 'Unknown'),
                    'Priority': ticket_data.get('priority', ''),
                    'Status': ticket_data.get('status', 'open'),
                    'Temp Status': f"TEMP ({temp_stage})" if is_temp else "",
                    'Subcategory': final_subcategory,
                    'Affectation Team': affectation_team,
                    'Submitted At': date_str,
                    'Resolved At': resolved_str,
                    'Description': ticket_data.get('description', '')[:100] + '...' if len(ticket_data.get('description', '')) > 100 else ticket_data.get('description', ''),
                    'User': user_name,
                    'Location': user_location,
                    'Thread ID': ticket_data.get('thread_id', '')
                })
        df = pd.DataFrame(data)
        if not df.empty:
            if 'Submitted At' in df.columns and df['Submitted At'].dtype == 'object':
                try:
                    df['Submitted At'] = pd.to_datetime(df['Submitted At'], errors='coerce')
                except:
                    pass
        return df

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
                st.write("**Ticket ID:** {}".format(ticket_id))
                
                # Handle both dictionary and Ticket object formats
                if hasattr(ticket, 'to_dict'):
                    # It's a Ticket object
                    st.write("**Type:** {}".format(ticket.ticket_type))
                    st.write("**Priority:** {}".format(ticket.priority))
                    st.write("**Status:** {}".format(ticket.status))
                    
                    # Show affectation team if available
                    if hasattr(ticket, 'affectation_team') and ticket.affectation_team:
                        st.write("**Affectation Team:** {}".format(ticket.affectation_team))
                        
                    st.write("**Submitted At:** {}".format(
                        ticket.date_submitted.strftime('%Y-%m-%d %H:%M:%S') 
                        if hasattr(ticket.date_submitted, 'strftime') else ticket.date_submitted
                    ))
                    if ticket.date_resolved:
                        st.write("**Resolved At:** {}".format(
                            ticket.date_resolved.strftime('%Y-%m-%d %H:%M:%S')
                            if hasattr(ticket.date_resolved, 'strftime') else ticket.date_resolved
                        ))
                    
                    st.subheader("User Information")
                    user = ticket.user
                    if isinstance(user, dict):
                        st.write("**Name:** {}".format(user.get('name', 'Unknown')))
                        st.write("**Email:** {}".format(user.get('email', '')))
                        st.write("**Location:** {}".format(user.get('location', '')))
                else:
                    # It's a dictionary
                    st.write("**Type:** {}".format(ticket.get('ticket_type', 'Unknown')))
                    st.write("**Priority:** {}".format(ticket.get('priority', '')))
                    st.write("**Status:** {}".format(ticket.get('status', 'open')))
                    
                    # Show affectation team if available
                    affectation_team = ticket.get('affectation_team', '')
                    if affectation_team:
                        st.write("**Affectation Team:** {}".format(affectation_team))
                    
                    date_submitted = ticket.get('date_submitted')
                    if date_submitted:
                        if isinstance(date_submitted, str):
                            st.write("**Submitted At:** {}".format(date_submitted))
                        elif hasattr(date_submitted, 'strftime'):
                            st.write("**Submitted At:** {}".format(date_submitted.strftime('%Y-%m-%d %H:%M:%S')))
                        else:
                            st.write("**Submitted At:** {}".format(str(date_submitted)))
                    
                    date_resolved = ticket.get('date_resolved')
                    if date_resolved:
                        if isinstance(date_resolved, str):
                            st.write("**Resolved At:** {}".format(date_resolved))
                        elif hasattr(date_resolved, 'strftime'):
                            st.write("**Resolved At:** {}".format(date_resolved.strftime('%Y-%m-%d %H:%M:%S')))
                        else:
                            st.write("**Resolved At:** {}".format(str(date_resolved)))
                    
                    st.subheader("User Information")
                    user = ticket.get('user', {})
                    if isinstance(user, dict):
                        st.write("**Name:** {}".format(user.get('name', 'Unknown')))
                        st.write("**Email:** {}".format(user.get('email', '')))
                        st.write("**Location:** {}".format(user.get('location', '')))
            
            with col2:
                st.subheader("Description")
                if hasattr(ticket, 'description'):
                    st.write(ticket.description)
                else:
                    st.write(ticket.get('description', 'No description'))
                
                # Show subcategories
                subcategories = None
                final_subcategory = None
                if hasattr(ticket, 'subcategories'):
                    subcategories = ticket.subcategories
                    final_subcategory = ticket.final_subcategory if hasattr(ticket, 'final_subcategory') else ""
                else:
                    subcategories = ticket.get('subcategories', [])
                    final_subcategory = ticket.get('final_subcategory', "")
                
                if final_subcategory:
                    st.markdown("#### Subcategory")
                    st.write(f"**Final Subcategory:** {final_subcategory}")
                elif subcategories:
                    st.markdown("#### Subcategories")
                    for subcat in subcategories:
                        if isinstance(subcat, dict):
                            if 'subcategory' in subcat:
                                st.write(f"- {subcat['subcategory']} (Confidence: {subcat.get('confidence', 'N/A')})")
                            elif 'category' in subcat:
                                st.write(f"- {subcat['category']} (Confidence: {subcat.get('confidence', 'N/A')})")
                        else:
                            st.write(f"- {subcat}")
                else:
                    st.write("No subcategory information available")
                
                # Show thread ID if available
                thread_id = None
                if hasattr(ticket, 'thread_id'):
                    thread_id = ticket.thread_id
                else:
                    thread_id = ticket.get('thread_id', None)
                
                if thread_id:
                    st.subheader("Thread Information")
                    st.write("**Thread ID:** {}".format(thread_id))
                
                # Show notes if available
                notes = None
                if hasattr(ticket, 'notes'):
                    notes = ticket.notes
                else:
                    notes = ticket.get('notes', [])
                
                if notes:
                    st.subheader("Additional Notes")
                    for note in notes:
                        st.write("- {}".format(note))

    def check_for_new_tickets(self) -> List[Dict]:
        # Remove self.load_tickets_from_filesystem()
        new_tickets = []
        tickets = self.ticket_manager.get_all_tickets()
        current_ticket_ids = set(tickets.keys())
        new_ticket_ids = current_ticket_ids - st.session_state.known_tickets
        for ticket_id in new_ticket_ids:
            ticket_data = tickets[ticket_id]
            
            # Extract ticket information, handling both object and dictionary formats
            if hasattr(ticket_data, 'to_dict'):
                # It's a Ticket object
                ticket_type = ticket_data.ticket_type
                priority = ticket_data.priority
                description = ticket_data.description
                is_temp = ticket_data.is_temp if hasattr(ticket_data, 'is_temp') else False
                temp_stage = ticket_data.stage if hasattr(ticket_data, 'stage') and is_temp else ""
                affectation_team = ticket_data.affectation_team if hasattr(ticket_data, 'affectation_team') else ""
                if hasattr(ticket_data.date_submitted, 'strftime'):
                    submitted_at = ticket_data.date_submitted.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    submitted_at = str(ticket_data.date_submitted)
            else:
                # It's a dictionary
                ticket_type = ticket_data.get('ticket_type', 'Unknown')
                priority = ticket_data.get('priority', '')
                description = ticket_data.get('description', '')
                is_temp = ticket_data.get('is_temp', False)
                temp_stage = ticket_data.get('stage', '') if is_temp else ""
                affectation_team = ticket_data.get('affectation_team', '')
                
                date_submitted = ticket_data.get('date_submitted')
                if isinstance(date_submitted, str):
                    submitted_at = date_submitted
                elif hasattr(date_submitted, 'strftime'):
                    submitted_at = date_submitted.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    submitted_at = str(date_submitted)
            
            # Trim description if too long
            if len(description) > 100:
                description = description[:100] + '...'
                
            new_tickets.append({
                'id': ticket_id,
                'type': ticket_type,
                'priority': priority,
                'description': description,
                'submitted_at': submitted_at,
                'is_temp': is_temp,
                'temp_stage': temp_stage,
                'affectation_team': affectation_team
            })
        st.session_state.known_tickets = current_ticket_ids
        st.session_state.last_update = datetime.now()
        if new_tickets:
            st.session_state.recent_activity = new_tickets
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
        
        # Reload tickets from filesystem to get fresh data
        # Remove self.load_tickets_from_filesystem()
        
        # Get min and max dates from tickets
        df = self.get_tickets_dataframe()
        filter_by_date = False
        start_date = None
        end_date = None
        min_date = None
        max_date = None
        date_filter_active = False
        
        if not df.empty:
            # Convert string dates to datetime objects if needed
            if df['Submitted At'].dtype != 'datetime64[ns]':
                try:
                    df['Submitted At'] = pd.to_datetime(df['Submitted At'], errors='coerce')
                except:
                    pass
            if not df['Submitted At'].isnull().all():
                min_date = df['Submitted At'].min().date()
                max_date = df['Submitted At'].max().date()
                
                # Sidebar toggle for date filtering
                filter_by_date = st.sidebar.checkbox("Filter by date range", value=False)
                
                if filter_by_date:
                    # Quick presets
                    preset = st.sidebar.radio(
                        "Quick presets",
                        options=["All time", "Last 7 days", "Last 30 days", "This month", "Custom"],
                        index=0,
                        horizontal=True
                    )
                    # Set default range based on preset
                    if preset == "All time":
                        start_date = min_date
                        end_date = max_date
                    elif preset == "Last 7 days":
                        start_date = max(min_date, (max_date - timedelta(days=6)))
                        end_date = max_date
                    elif preset == "Last 30 days":
                        start_date = max(min_date, (max_date - timedelta(days=29)))
                        end_date = max_date
                    elif preset == "This month":
                        start_date = max(min_date, max_date.replace(day=1))
                        end_date = max_date
                    else:  # Custom
                        start_date = min_date
                        end_date = max_date
                    # If only one date is available
                    if min_date == max_date:
                        st.sidebar.info(f"Only tickets from {min_date.strftime('%Y-%m-%d')} are available")
                        start_date = min_date
                        end_date = max_date
                    elif preset == "Custom":
                        start_date = st.sidebar.date_input(
                            "From",
                            value=start_date,
                            min_value=min_date,
                            max_value=max_date,
                            key="date_from"
                        )
                        end_date = st.sidebar.date_input(
                            "To",
                            value=end_date,
                            min_value=min_date,
                            max_value=max_date,
                            key="date_to"
                        )
                        # Ensure valid range
                        if start_date > end_date:
                            st.sidebar.warning("Start date cannot be after end date. Resetting to full range.")
                            start_date = min_date
                            end_date = max_date
                    date_filter_active = True
                else:
                    # Show all tickets
                    start_date = min_date
                    end_date = max_date
                    date_filter_active = False
                st.sidebar.markdown("---")
            else:
                st.sidebar.warning("No valid dates found in tickets")
        else:
            st.sidebar.warning("No tickets found")
        
        # Get available ticket types, priorities, and statuses from the data
        available_types = sorted(df['Type'].unique().tolist()) if not df.empty else ["Incident", "Demande"]
        available_priorities = sorted(df['Priority'].unique().tolist()) if not df.empty else ["CRITIQUE", "ELEVEE"]
        available_statuses = sorted(df['Status'].unique().tolist()) if not df.empty else ["open", "in-progress", "closed"]
        
        st.sidebar.subheader("Category Filters")
        ticket_type = st.sidebar.multiselect(
            "Ticket Type",
            options=available_types,
            default=available_types
        )
        
        priority = st.sidebar.multiselect(
            "Priority",
            options=available_priorities,
            default=available_priorities
        )
        
        status = st.sidebar.multiselect(
            "Status",
            options=available_statuses,
            default=available_statuses
        )
        
        # Add a filter for temporary tickets
        include_temp_tickets = st.sidebar.checkbox("Show Temporary Tickets", value=True)
        if include_temp_tickets:
            st.sidebar.info("Temporary tickets are shown with a 'TEMP' status and represent tickets in progress.")

        # Reset notifications button
        st.sidebar.markdown("---")
        st.sidebar.subheader("Actions")
        if st.sidebar.button("Reset Notifications"):
            st.session_state.known_tickets = set()
            st.session_state.recent_activity = []
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
                        # Add a visual indicator for temporary tickets
                        is_temp = ticket.get('is_temp', False)
                        temp_stage = ticket.get('temp_stage', '')
                        
                        # Choose between regular info box and a different styling for temp tickets
                        if is_temp:
                            # Use warning style for temporary tickets
                            st.warning("""
                            **Temporary Ticket{stage}**
                            - ID: {id}
                            - Type: {type}
                            - Priority: {priority}
                            - Affectation Team: {team}
                            - Submitted: {submitted_at}
                            - Description: {description}
                            """.format(
                                stage=f" ({temp_stage})" if temp_stage else "",
                                id=ticket['id'],
                                type=ticket['type'],
                                priority=ticket['priority'],
                                team=ticket.get('affectation_team', 'N/A'),
                                submitted_at=ticket['submitted_at'],
                                description=ticket['description']
                            ))
                        else:
                            # Use regular info style for final tickets
                            st.info("""
                            **Recent Ticket Activity**
                            - ID: {id}
                            - Type: {type}
                            - Priority: {priority}
                            - Affectation Team: {team}
                            - Submitted: {submitted_at}
                            - Description: {description}
                            """.format(
                                id=ticket['id'],
                                type=ticket['type'],
                                priority=ticket['priority'],
                                team=ticket.get('affectation_team', 'N/A'),
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
            
            # Apply date filter if enabled
            if not df.empty and start_date and end_date and (not filter_by_date or date_filter_active):
                if filter_by_date and date_filter_active:
                    # Convert string dates to datetime for filtering if needed
                    if df['Submitted At'].dtype != 'datetime64[ns]':
                        try:
                            df['Submitted At'] = pd.to_datetime(df['Submitted At'], errors='coerce')
                        except:
                            pass
                    # Filter by date range
                    if not df['Submitted At'].isnull().all():
                        mask = (df['Submitted At'].dt.date >= start_date) & (df['Submitted At'].dt.date <= end_date)
                        df = df[mask]
                # Show date range indicator if filter is active and not all time
                if filter_by_date and date_filter_active and (start_date != min_date or end_date != max_date):
                    st.caption(f"Filtered by date: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Apply other filters
            if ticket_type and 'Type' in df.columns:
                df = df[df['Type'].isin(ticket_type)]
            if priority and 'Priority' in df.columns:
                df = df[df['Priority'].isin(priority)]
            if status and 'Status' in df.columns:
                df = df[df['Status'].isin(status)]
                
            # Apply temp ticket filter
            if not include_temp_tickets and 'Temp Status' in df.columns:
                df = df[df['Temp Status'] == ""]
                
            # Add active filters information
            if not df.empty and 'start_date' in locals() and 'end_date' in locals() and 'min_date' in locals() and 'max_date' in locals():
                if start_date != min_date or end_date != max_date:
                    st.caption("Filtered by date: {} to {}".format(
                        start_date.strftime('%Y-%m-%d'), 
                        end_date.strftime('%Y-%m-%d')
                    ))
            
            # Sort tickets by submission date (newest first)
            if not df.empty:
                # Make sure 'Submitted At' is datetime for proper sorting
                if df['Submitted At'].dtype != 'datetime64[ns]':
                    try:
                        df['Submitted At'] = pd.to_datetime(df['Submitted At'], errors='coerce')
                    except:
                        st.warning("Could not convert dates to datetime for sorting")
                
                # Sort by submission date in descending order
                if not df['Submitted At'].isnull().all():
                    df = df.sort_values(by='Submitted At', ascending=False)
                
                # Convert back to string for display if needed
                if df['Submitted At'].dtype == 'datetime64[ns]':
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
                        
                        # Get priority for coloring
                        priority_value = ""
                        if hasattr(ticket, 'priority'):
                            priority_value = ticket.priority
                        else:
                            priority_value = ticket.get('priority', '')
                        
                        # Check if it's a temporary ticket
                        is_temp = False
                        temp_stage = ""
                        if hasattr(ticket, 'is_temp'):
                            is_temp = ticket.is_temp
                            temp_stage = ticket.stage if hasattr(ticket, 'stage') else ""
                        else:
                            is_temp = ticket.get('is_temp', False)
                            temp_stage = ticket.get('stage', "")
                        
                        # Create a colored container based on priority
                        priority_colors = {
                            "CRITIQUE": "darkred",
                            "ELEVEE": "orange",
                            "MOYENNE": "blue",
                            "BASSE": "green"
                        }
                        
                        priority_color = priority_colors.get(priority_value, "gray")
                        
                        # Add special styling for temporary tickets
                        temp_style = """
                        border: 2px dashed #888;
                        background-color: rgba(200,200,200,0.15);
                        """ if is_temp else ""
                        
                        st.markdown(f"""
                        <div style="padding: 10px; border-radius: 5px; border-left: 5px solid {priority_color}; {temp_style} background-color: rgba(0,0,0,0.05);">
                        """, unsafe_allow_html=True)
                        
                        details_col1, details_col2 = st.columns(2)
                        
                        with details_col1:
                            st.markdown("#### Basic Information")
                            st.write("**Ticket ID:** {}".format(ticket_id))
                            
                            # Display temporary status if applicable
                            if is_temp:
                                st.markdown(f"<span style='color: #888; font-weight: bold; background-color: #f0f0f0; padding: 2px 6px; border-radius: 3px;'>TEMPORARY ({temp_stage})</span>", unsafe_allow_html=True)
                                
                            # Type
                            if hasattr(ticket, 'ticket_type'):
                                st.write("**Type:** {}".format(ticket.ticket_type))
                            else:
                                st.write("**Type:** {}".format(ticket.get('ticket_type', 'Unknown')))
                                
                            # Priority    
                            if hasattr(ticket, 'priority'):
                                st.write("**Priority:** {}".format(ticket.priority))
                            else:
                                st.write("**Priority:** {}".format(ticket.get('priority', '')))
                                
                            # Status
                            if hasattr(ticket, 'status'):
                                st.write("**Status:** {}".format(ticket.status))
                            else:
                                st.write("**Status:** {}".format(ticket.get('status', 'open')))
                                
                            # Affectation Team
                            if hasattr(ticket, 'affectation_team') and ticket.affectation_team:
                                st.write("**Affectation Team:** {}".format(ticket.affectation_team))
                            elif not hasattr(ticket, 'affectation_team') and ticket.get('affectation_team', ''):
                                st.write("**Affectation Team:** {}".format(ticket.get('affectation_team', '')))
                                
                            # Dates
                            date_submitted = None
                            if hasattr(ticket, 'date_submitted'):
                                date_submitted = ticket.date_submitted
                            else:
                                date_submitted = ticket.get('date_submitted')
                                
                            if date_submitted:
                                if hasattr(date_submitted, 'strftime'):
                                    st.write("**Submitted At:** {}".format(date_submitted.strftime('%Y-%m-%d %H:%M:%S')))
                                else:
                                    st.write("**Submitted At:** {}".format(date_submitted))
                            
                            date_resolved = None
                            if hasattr(ticket, 'date_resolved'):
                                date_resolved = ticket.date_resolved
                            else:
                                date_resolved = ticket.get('date_resolved')
                                
                            if date_resolved:
                                if hasattr(date_resolved, 'strftime'):
                                    st.write("**Resolved At:** {}".format(date_resolved.strftime('%Y-%m-%d %H:%M:%S')))
                                else:
                                    st.write("**Resolved At:** {}".format(date_resolved))
                            
                            # User information
                            st.markdown("#### User Information")
                            user = None
                            if hasattr(ticket, 'user'):
                                user = ticket.user
                            else:
                                user = ticket.get('user', {})
                                
                            if isinstance(user, dict):
                                st.write("**Name:** {}".format(user.get('name', 'Unknown')))
                                st.write("**Email:** {}".format(user.get('email', '')))
                                st.write("**Location:** {}".format(user.get('location', '')))
                            else:
                                st.write("**User:** {}".format(str(user)))
                        
                        with details_col2:
                            st.markdown("#### Description")
                            description = None
                            if hasattr(ticket, 'description'):
                                description = ticket.description
                            else:
                                description = ticket.get('description', '')
                                
                            st.write(description)
                            
                            # Subcategories
                            subcategories = None
                            final_subcategory = None
                            if hasattr(ticket, 'subcategories'):
                                subcategories = ticket.subcategories
                                final_subcategory = ticket.final_subcategory if hasattr(ticket, 'final_subcategory') else ""
                            else:
                                subcategories = ticket.get('subcategories', [])
                                final_subcategory = ticket.get('final_subcategory', "")
                                
                            if final_subcategory:
                                st.markdown("#### Subcategory")
                                st.write(f"**Final Subcategory:** {final_subcategory}")
                            elif subcategories:
                                st.markdown("#### Subcategories")
                                for subcat in subcategories:
                                    if isinstance(subcat, dict):
                                        if 'subcategory' in subcat:
                                            st.write(f"- {subcat['subcategory']} (Confidence: {subcat.get('confidence', 'N/A')})")
                                        elif 'category' in subcat:
                                            st.write(f"- {subcat['category']} (Confidence: {subcat.get('confidence', 'N/A')})")
                                    else:
                                        st.write(f"- {subcat}")
                            
                            # Thread ID
                            thread_id = None
                            if hasattr(ticket, 'thread_id'):
                                thread_id = ticket.thread_id
                            else:
                                thread_id = ticket.get('thread_id')
                                
                            if thread_id:
                                st.markdown("#### Thread Information")
                                st.write("**Thread ID:** {}".format(thread_id))
                            
                            # Notes
                            notes = None
                            if hasattr(ticket, 'notes'):
                                notes = ticket.notes
                            else:
                                notes = ticket.get('notes', [])
                                
                            if notes:
                                st.markdown("#### Additional Notes")
                                for note in notes:
                                    st.write("- {}".format(note))
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.warning(f"Ticket {ticket_id} not found in ticket manager")

        # Auto-refresh using st.rerun()
        time.sleep(self.update_interval)
        st.rerun()

if __name__ == "__main__":
    dashboard = Dashboard()
    dashboard.run() 