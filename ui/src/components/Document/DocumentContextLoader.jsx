import React, { Component } from 'react';
import { connect } from 'react-redux';

import { fetchDocument, fetchEntityTags, queryEntities } from 'src/actions';
import { selectEntity, selectEntityTags } from 'src/selectors';


class DocumentContextLoader extends Component {
  componentDidMount() {
    this.fetchIfNeeded();
  }

  componentDidUpdate(prevProps) {
    this.fetchIfNeeded();
  }

  fetchIfNeeded() {
    const { documentId, document } = this.props;
    if (document.shouldLoad) {
      this.props.fetchDocument({ id: documentId });
    }

    const { tagsResult } = this.props;
    if (tagsResult.shouldLoad) {
      this.props.fetchEntityTags({ id: documentId });
    }
  }

  render() {
    return <React.Fragment>{this.props.children}</React.Fragment>;
  }
}


const mapStateToProps = (state, ownProps) => {
  const { documentId } = ownProps;
  return {
    document: selectEntity(state, documentId),
    tagsResult: selectEntityTags(state, documentId)
  };
};

DocumentContextLoader = connect(mapStateToProps, { fetchDocument, fetchEntityTags, queryEntities })(DocumentContextLoader);
export default DocumentContextLoader;
