import React, { Component } from 'react';

export default class BaseComponent extends Component {
  constructor(props) {
    super(props);
    this.state = { loading: false, error: null };
    this.mounted = false;
  }

  componentDidMount() {
    this.mounted = true;
  }

  componentWillUnmount() {
    this.mounted = false;
  }

  setLoading(loading) {
    if (this.mounted) this.setState({ loading });
  }

  setError(error) {
    if (this.mounted) this.setState({ error });
  }

  clearError() {
    if (this.mounted) this.setState({ error: null });
  }

  render() {
    return null;
  }
}
